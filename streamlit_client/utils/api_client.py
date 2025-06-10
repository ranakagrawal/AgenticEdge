"""
API Client for communicating with FastAPI backend
"""

import requests
import json
import sys
import os
from typing import Dict, Any, Optional
import streamlit as st

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_ENDPOINTS, UI_MESSAGES


class APIClient:
    """Client for making API calls to the FastAPI backend."""
    
    def __init__(self):
        self.base_url = API_ENDPOINTS["root"].rstrip("/")
        self.session = requests.Session()
        
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and return JSON data."""
        try:
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False, 
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {"success": False, "error": f"Response parsing error: {str(e)}"}
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health status."""
        try:
            response = self.session.get(API_ENDPOINTS["health"], timeout=5)
            return self._handle_response(response)
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": UI_MESSAGES["connection_error"]}
        except Exception as e:
            return {"success": False, "error": f"Health check failed: {str(e)}"}
    
    def get_auth_url(self) -> Dict[str, Any]:
        """Get Google OAuth authorization URL."""
        try:
            response = self.session.get(API_ENDPOINTS["auth_google"], timeout=10)
            return self._handle_response(response)
        except Exception as e:
            return {"success": False, "error": f"Auth URL request failed: {str(e)}"}
    
    def handle_auth_callback(self, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """Handle OAuth callback with authorization code."""
        try:
            params = {"code": code}
            if state:
                params["state"] = state
                
            response = self.session.get(
                API_ENDPOINTS["auth_callback"], 
                params=params,
                timeout=15
            )
            return self._handle_response(response)
        except Exception as e:
            return {"success": False, "error": f"Auth callback failed: {str(e)}"}
    
    def process_emails(self, user_id: str, days_back: int = 180, max_emails: int = 100) -> Dict[str, Any]:
        """Start email processing for a user."""
        try:
            url = f"{API_ENDPOINTS['process_emails']}/{user_id}"
            payload = {
                "days_back": days_back,
                "max_emails": max_emails
            }
            
            response = self.session.post(
                url,
                json=payload,
                timeout=120  # Increased timeout for email processing
            )
            return self._handle_response(response)
        except Exception as e:
            return {"success": False, "error": f"Email processing failed: {str(e)}"}
    
    def get_processing_status(self, run_id: str) -> Dict[str, Any]:
        """Get processing status for a run ID."""
        try:
            url = f"{API_ENDPOINTS['process_status']}/{run_id}"
            response = self.session.get(url, timeout=10)
            return self._handle_response(response)
        except Exception as e:
            return {"success": False, "error": f"Status check failed: {str(e)}"}
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information."""
        try:
            url = f"{API_ENDPOINTS['user_profile']}/{user_id}/profile"
            response = self.session.get(url, timeout=10)
            return self._handle_response(response)
        except Exception as e:
            return {"success": False, "error": f"Profile fetch failed: {str(e)}"}
    
    def get_user_entities(self, user_id: str, entity_type: Optional[str] = None, 
                         category: Optional[str] = None) -> Dict[str, Any]:
        """Get extracted entities for a user."""
        try:
            url = f"{API_ENDPOINTS['user_entities']}/{user_id}/entities"
            params = {}
            if entity_type:
                params["entity_type"] = entity_type
            if category:
                params["category"] = category
                
            response = self.session.get(url, params=params, timeout=15)
            return self._handle_response(response)
        except Exception as e:
            return {"success": False, "error": f"Entities fetch failed: {str(e)}"}
    
    def delete_user_data(self, user_id: str) -> Dict[str, Any]:
        """Delete all user data."""
        try:
            url = f"{API_ENDPOINTS['user_profile']}/{user_id}"
            response = self.session.delete(url, timeout=10)
            return self._handle_response(response)
        except Exception as e:
            return {"success": False, "error": f"User deletion failed: {str(e)}"}


# Global API client instance
@st.cache_resource
def get_api_client() -> APIClient:
    """Get cached API client instance."""
    return APIClient() 