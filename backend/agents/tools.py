"""Tools for CrewAI agents in the finance email processing pipeline."""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from loguru import logger

from backend.models.entities import PaymentEntity, EntityType, EntityCategory, EntityStatus


class EmailProcessingTool(BaseTool):
    """Tool for preprocessing email content."""
    
    name: str = "Email Preprocessing Tool"
    description: str = "Cleans and preprocesses email content for better LLM processing"
    
    def _run(self, email_data: Dict[str, Any]) -> str:
        """Clean and preprocess email content."""
        try:
            # Extract relevant fields
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')
            sender = email_data.get('from', '')
            
            # Clean HTML if present
            if '<' in body and '>' in body:
                soup = BeautifulSoup(body, 'html.parser')
                body = soup.get_text()
            
            # Remove excessive whitespace
            body = re.sub(r'\s+', ' ', body).strip()
            
            # Remove common noise
            noise_patterns = [
                r'This email was sent to.*',
                r'If you no longer wish to receive.*',
                r'Unsubscribe.*',
                r'Privacy Policy.*',
                r'Terms of Service.*',
                r'Download our app.*',
                r'Follow us on.*'
            ]
            
            for pattern in noise_patterns:
                body = re.sub(pattern, '', body, flags=re.IGNORECASE)
            
            # Create clean text for processing
            clean_text = f"""
            EMAIL SUBJECT: {subject}
            FROM: {sender}
            CONTENT: {body[:2000]}  # Limit content to avoid token limits
            """
            
            return clean_text.strip()
            
        except Exception as e:
            logger.error(f"Error preprocessing email: {e}")
            return f"Error processing email: {str(e)}"


class EntityExtractionTool(BaseTool):
    """Tool for extracting financial entities from email content using LLM."""
    
    name: str = "Entity Extraction Tool"
    description: str = "Extracts structured financial information from email content"
    
    def _run(self, clean_email_text: str) -> str:
        """Extract financial entities from clean email text."""
        
        extraction_prompt = f"""
        You are a financial data extraction expert specializing in Indian financial emails.
        
        Extract financial information from the following email and return a JSON object with these fields:
        
        {{
            "merchant": "Name of the service provider/merchant",
            "amount": "Numeric amount (float)",
            "currency": "Currency code (usually INR)",
            "due_date": "Due date in YYYY-MM-DD format",
            "entity_type": "subscription|bill|loan",
            "category": "entertainment|productivity|cloud_storage|utility|credit_card|municipal|medical|miscellaneous|home_loan|personal_loan|education_loan|vehicle_loan|bnpl",
            "auto_debit": "true|false",
            "billing_cycle": "monthly|quarterly|yearly|one-time (for subscriptions)",
            "principal_amount": "Principal amount for loans (if applicable)",
            "interest_amount": "Interest amount for loans (if applicable)",
            "late_fee": "Late fee amount (if mentioned)",
            "confidence_score": "Confidence level 0.0-1.0"
        }}
        
        Guidelines:
        1. Look for Indian Rupee amounts (₹, Rs., INR)
        2. Identify subscription services (Netflix, Prime, etc.)
        3. Recognize bank/credit card statements
        4. Detect utility bills (electricity, mobile, internet)
        5. Identify loan EMIs and payment schedules
        6. Extract due dates carefully
        7. Set confidence_score based on clarity of information
        8. If information is unclear or missing, use null values
        9. Focus on actionable payment information
        
        Email Content:
        {clean_email_text}
        
        Return only valid JSON, no additional text.
        """
        
        # This would typically call an LLM like OpenAI GPT-4
        # For now, return the prompt that would be sent to the LLM
        return extraction_prompt


class SchemaValidationTool(BaseTool):
    """Tool for validating extracted entity data against schema."""
    
    name: str = "Schema Validation Tool"
    description: str = "Validates extracted financial entity data against predefined schema"
    
    def _run(self, extracted_data: str) -> str:
        """Validate extracted entity data."""
        try:
            # Parse JSON response
            if not extracted_data.strip():
                return json.dumps({"valid": False, "errors": ["Empty data"]})
            
            try:
                data = json.loads(extracted_data)
            except json.JSONDecodeError as e:
                return json.dumps({"valid": False, "errors": [f"Invalid JSON: {str(e)}"]})
            
            errors = []
            
            # Required fields validation
            required_fields = ['merchant', 'amount', 'entity_type', 'category']
            for field in required_fields:
                if field not in data or not data[field]:
                    errors.append(f"Missing required field: {field}")
            
            # Type validations
            if 'amount' in data:
                try:
                    amount = float(data['amount'])
                    if amount <= 0:
                        errors.append("Amount must be positive")
                except (ValueError, TypeError):
                    errors.append("Amount must be a valid number")
            
            # Date validation
            if 'due_date' in data and data['due_date']:
                try:
                    datetime.strptime(data['due_date'], '%Y-%m-%d')
                except ValueError:
                    errors.append("Due date must be in YYYY-MM-DD format")
            
            # Enum validations
            valid_entity_types = ['subscription', 'bill', 'loan']
            if 'entity_type' in data and data['entity_type'] not in valid_entity_types:
                errors.append(f"Invalid entity_type. Must be one of: {valid_entity_types}")
            
            valid_categories = [
                'entertainment', 'productivity', 'cloud_storage', 'utility',
                'credit_card', 'municipal', 'medical', 'miscellaneous',
                'home_loan', 'personal_loan', 'education_loan', 'vehicle_loan', 'bnpl'
            ]
            if 'category' in data and data['category'] not in valid_categories:
                errors.append(f"Invalid category. Must be one of: {valid_categories}")
            
            # Confidence score validation
            if 'confidence_score' in data:
                try:
                    score = float(data['confidence_score'])
                    if not 0.0 <= score <= 1.0:
                        errors.append("Confidence score must be between 0.0 and 1.0")
                except (ValueError, TypeError):
                    errors.append("Confidence score must be a valid number")
            
            result = {
                "valid": len(errors) == 0,
                "errors": errors,
                "validated_data": data if len(errors) == 0 else None
            }
            
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Error validating schema: {e}")
            return json.dumps({"valid": False, "errors": [f"Validation error: {str(e)}"]})


class ClassificationTool(BaseTool):
    """Tool for classifying financial entities into categories."""
    
    name: str = "Entity Classification Tool"
    description: str = "Classifies financial entities and determines processing rules"
    
    def _run(self, validated_entity: str) -> str:
        """Classify entity and determine processing rules."""
        try:
            data = json.loads(validated_entity)
            
            merchant = data.get('merchant', '').lower()
            entity_type = data.get('entity_type', '')
            
            # Enhanced classification based on merchant patterns
            classification_rules = {
                'subscriptions': {
                    'patterns': ['netflix', 'prime', 'hotstar', 'spotify', 'youtube', 'disney', 'canva', 'notion', 'dropbox', 'google'],
                    'default_category': 'entertainment',
                    'billing_cycle': 'monthly'
                },
                'utilities': {
                    'patterns': ['bses', 'tata', 'reliance', 'airtel', 'jio', 'vodafone', 'bharti'],
                    'default_category': 'utility',
                    'billing_cycle': 'monthly'
                },
                'credit_cards': {
                    'patterns': ['hdfc', 'icici', 'sbi', 'axis', 'amex', 'mastercard', 'visa'],
                    'default_category': 'credit_card',
                    'billing_cycle': 'monthly'
                },
                'loans': {
                    'patterns': ['home loan', 'personal loan', 'car loan', 'education loan', 'emi'],
                    'default_category': 'home_loan',
                    'billing_cycle': 'monthly'
                }
            }
            
            # Apply classification rules
            for category, rules in classification_rules.items():
                for pattern in rules['patterns']:
                    if pattern in merchant:
                        if not data.get('category'):
                            data['category'] = rules['default_category']
                        if not data.get('billing_cycle'):
                            data['billing_cycle'] = rules['billing_cycle']
                        break
            
            # Set default values
            if not data.get('currency'):
                data['currency'] = 'INR'
            
            if not data.get('status'):
                data['status'] = 'pending'
            
            # Auto-debit detection
            if not data.get('auto_debit'):
                auto_debit_indicators = ['auto', 'automatic', 'recurring', 'autopay']
                content = data.get('original_content', '').lower()
                data['auto_debit'] = any(indicator in content for indicator in auto_debit_indicators)
            
            result = {
                "classified": True,
                "entity_data": data,
                "processing_rules": {
                    "requires_reminder": data.get('status') == 'pending',
                    "track_renewal": data.get('entity_type') == 'subscription',
                    "calculate_interest": data.get('entity_type') == 'loan'
                }
            }
            
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Error classifying entity: {e}")
            return json.dumps({"classified": False, "error": str(e)})


class DeduplicationTool(BaseTool):
    """Tool for detecting and handling duplicate entities."""
    
    name: str = "Deduplication Tool"
    description: str = "Detects and handles duplicate financial entities"
    
    def _run(self, entity_data: str, existing_entities: str = "[]") -> str:
        """Check for duplicates and handle them."""
        try:
            current_entity = json.loads(entity_data)
            existing = json.loads(existing_entities) if existing_entities else []
            
            duplicates = []
            
            for existing_entity in existing:
                # Check for duplicates based on multiple criteria
                is_duplicate = self._is_duplicate(current_entity, existing_entity)
                if is_duplicate:
                    duplicates.append(existing_entity)
            
            result = {
                "is_duplicate": len(duplicates) > 0,
                "duplicate_count": len(duplicates),
                "duplicates": duplicates,
                "action": "skip" if len(duplicates) > 0 else "process",
                "entity_data": current_entity
            }
            
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Error checking duplicates: {e}")
            return json.dumps({"is_duplicate": False, "error": str(e)})
    
    def _is_duplicate(self, entity1: Dict, entity2: Dict) -> bool:
        """Check if two entities are duplicates."""
        # Same merchant and amount
        if (entity1.get('merchant', '').lower() == entity2.get('merchant', '').lower() and
            abs(float(entity1.get('amount', 0)) - float(entity2.get('amount', 0))) < 0.01):
            
            # Check date proximity (within 7 days)
            try:
                date1 = datetime.strptime(entity1.get('due_date', ''), '%Y-%m-%d')
                date2 = datetime.strptime(entity2.get('due_date', ''), '%Y-%m-%d')
                date_diff = abs((date1 - date2).days)
                
                if date_diff <= 7:
                    return True
            except ValueError:
                pass
        
        return False


class DatabaseTool(BaseTool):
    """Tool for database operations."""
    
    name: str = "Database Tool"
    description: str = "Handles database operations for financial entities"
    
    def _run(self, operation: str, data: str = "") -> str:
        """Perform database operations."""
        try:
            if operation == "save_entity":
                entity_data = json.loads(data)
                # In a real implementation, this would save to MongoDB
                # For now, just return success
                result = {
                    "saved": True,
                    "entity_id": f"entity_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                return json.dumps(result)
            
            elif operation == "get_existing_entities":
                # In a real implementation, this would query MongoDB
                # For now, return empty list
                return json.dumps([])
            
            else:
                return json.dumps({"error": f"Unknown operation: {operation}"})
                
        except Exception as e:
            logger.error(f"Database operation error: {e}")
            return json.dumps({"error": str(e)})


# Export all tools
__all__ = [
    'EmailProcessingTool',
    'EntityExtractionTool', 
    'SchemaValidationTool',
    'ClassificationTool',
    'DeduplicationTool',
    'DatabaseTool'
] 