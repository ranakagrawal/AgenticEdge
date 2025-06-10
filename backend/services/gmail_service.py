"""Gmail service for OAuth authentication and email fetching."""

import base64
import email
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.config import settings
from backend.models.entities import UserProfile
from loguru import logger


class GmailService:
    """Service for Gmail API operations."""
    
    def __init__(self):
        self.scopes = settings.gmail_scopes
        
    def get_auth_flow(self) -> Flow:
        """Create OAuth2 flow for Gmail authentication."""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.google_redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = settings.google_redirect_uri
        return flow
    
    def get_authorization_url(self) -> str:
        """Get authorization URL for OAuth flow."""
        flow = self.get_auth_flow()
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        flow = self.get_auth_flow()
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None
        }
    
    def build_service(self, access_token: str, refresh_token: str):
        """Build Gmail API service with credentials."""
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=self.scopes
        )
        
        # Refresh token if expired
        if credentials.expired:
            credentials.refresh(Request())
            
        return build('gmail', 'v1', credentials=credentials)
    
    def get_user_info(self, access_token: str, refresh_token: str) -> Dict[str, Any]:
        """Get user profile information."""
        service = self.build_service(access_token, refresh_token)
        
        try:
            profile = service.users().getProfile(userId='me').execute()
            return {
                "email": profile['emailAddress'],
                "total_messages": profile.get('messagesTotal', 0),
                "threads_total": profile.get('threadsTotal', 0)
            }
        except HttpError as error:
            logger.error(f"Error getting user profile: {error}")
            raise
    
    def get_financial_emails(
        self, 
        access_token: str, 
        refresh_token: str, 
        days_back: int = 180,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch financial emails from Gmail."""
        service = self.build_service(access_token, refresh_token)
        
        # Build query for financial emails
        query = self._build_financial_query(days_back)
        
        try:
            # Search for messages
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} financial emails")
            
            # Fetch full message details
            email_data = []
            for msg in messages:
                try:
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    parsed_email = self._parse_email_message(message)
                    if parsed_email:
                        email_data.append(parsed_email)
                        
                except HttpError as error:
                    logger.error(f"Error fetching message {msg['id']}: {error}")
                    continue
            
            logger.info(f"Successfully parsed {len(email_data)} emails")
            return email_data
            
        except HttpError as error:
            logger.error(f"Error searching emails: {error}")
            raise
    
    def _build_financial_query(self, days_back: int) -> str:
        """Build Gmail search query for financial emails."""
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Indian financial institutions and services
        financial_senders = [
            # Banks
            'hdfc', 'icici', 'sbi', 'axis', 'kotak', 'pnb', 'bob', 'canara',
            'union', 'indian', 'yes', 'indus', 'rbl', 'idfc', 'dbs',
            
            # Credit Card Companies
            'americanexpress', 'amex', 'mastercard', 'visa',
            
            # Digital Payment Services
            'paytm', 'phonepe', 'gpay', 'amazon', 'flipkart', 'razorpay',
            'mobikwik', 'freecharge', 'airtel', 'jio', 'vodafone',
            
            # Subscription Services
            'netflix', 'prime', 'hotstar', 'spotify', 'youtube', 'disney',
            'zomato', 'swiggy', 'uber', 'ola', 'bookmyshow',
            
            # Utilities
            'bses', 'tata', 'reliance', 'adani', 'bharti', 'mahanagar',
            
            # Investment & Insurance
            'zerodha', 'groww', 'upstox', 'kuvera', 'lic', 'bajaj',
            'hdfc_life', 'sbi_life', 'icici_prudential'
        ]
        
        # Financial keywords
        keywords = [
            'bill', 'invoice', 'payment', 'due', 'statement', 'receipt',
            'subscription', 'renewal', 'emi', 'loan', 'credit', 'debit',
            'outstanding', 'balance', 'transaction', 'refund', 'charge'
        ]
        
        # Build query components
        sender_query = ' OR '.join([f'from:{sender}' for sender in financial_senders])
        keyword_query = ' OR '.join(keywords)
        
        # Combine with date filter
        query = f'({sender_query}) AND ({keyword_query}) after:{start_date.strftime("%Y/%m/%d")}'
        
        return query
    
    def _parse_email_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Gmail message into structured format."""
        try:
            headers = message['payload'].get('headers', [])
            
            # Extract headers
            email_data = {
                'message_id': message['id'],
                'thread_id': message['threadId'],
                'label_ids': message.get('labelIds', []),
                'snippet': message.get('snippet', ''),
                'internal_date': message.get('internalDate', ''),
                'subject': '',
                'from': '',
                'to': '',
                'date': '',
                'body': '',
                'attachments': []
            }
            
            # Parse headers
            for header in headers:
                name = header['name'].lower()
                value = header['value']
                
                if name == 'subject':
                    email_data['subject'] = value
                elif name == 'from':
                    email_data['from'] = value
                elif name == 'to':
                    email_data['to'] = value
                elif name == 'date':
                    email_data['date'] = value
            
            # Extract body content
            body_text = self._extract_body_text(message['payload'])
            email_data['body'] = body_text
            
            # Extract attachments info
            attachments = self._extract_attachments_info(message['payload'])
            email_data['attachments'] = attachments
            
            return email_data
            
        except Exception as error:
            logger.error(f"Error parsing email message: {error}")
            return None
    
    def _extract_body_text(self, payload: Dict[str, Any]) -> str:
        """Extract plain text body from email payload."""
        body_text = ""
        
        if 'parts' in payload:
            # Multi-part message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        data = part['body']['data']
                        body_text += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        data = part['body']['data']
                        html_content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        # Basic HTML to text conversion
                        text_content = re.sub(r'<[^>]+>', '', html_content)
                        body_text += text_content
        else:
            # Single part message
            if payload['mimeType'] == 'text/plain':
                if 'data' in payload['body']:
                    data = payload['body']['data']
                    body_text = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif payload['mimeType'] == 'text/html':
                if 'data' in payload['body']:
                    data = payload['body']['data']
                    html_content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    # Basic HTML to text conversion
                    body_text = re.sub(r'<[^>]+>', '', html_content)
        
        return body_text.strip()
    
    def _extract_attachments_info(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachment information from email payload."""
        attachments = []
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('filename'):
                    attachment_info = {
                        'filename': part['filename'],
                        'mime_type': part['mimeType'],
                        'size': part['body'].get('size', 0),
                        'attachment_id': part['body'].get('attachmentId')
                    }
                    attachments.append(attachment_info)
        
        return attachments 