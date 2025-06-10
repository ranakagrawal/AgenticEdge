"""Tools for CrewAI agents in the finance email processing pipeline."""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from loguru import logger
import uuid

from backend.models.entities import PaymentEntity, EntityType, EntityCategory, EntityStatus


class EmailProcessingTool(BaseTool):
    """Tool for preprocessing email content."""
    
    name: str = "Email Preprocessing Tool"
    description: str = "Cleans and preprocesses email content for better LLM processing. Accepts email data from task context or direct input."
    
    def _run(self, email_data: Any) -> str:
        """Clean and preprocess email content."""
        try:
            import json
            # Handle CrewAI task context or direct input
            if isinstance(email_data, str):
                # If string input, try to parse as JSON
                try:
                    email_data = json.loads(email_data)
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON input - {email_data[:100]}..."
            
            # Handle list of emails (from task context)
            if isinstance(email_data, list):
                cleaned_emails = []
                for email in email_data:
                    cleaned_emails.append(self._clean_single_email(email))
                return json.dumps(cleaned_emails)
            
            # Handle single email
            elif isinstance(email_data, dict):
                return self._clean_single_email(email_data)
            
            else:
                return f"Error: Unexpected input type - {type(email_data)}"
                
        except Exception as e:
            logger.error(f"Error preprocessing email: {e}")
            return f"Error processing email: {str(e)}"
    
    def _clean_single_email(self, email_data: Dict[str, Any]) -> str:
        """Clean a single email."""
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
            logger.error(f"Error cleaning single email: {e}")
            return f"Error cleaning email: {str(e)}"


class EntityExtractionTool(BaseTool):
    """Tool for extracting financial entities from email content using LLM."""
    
    name: str = "Entity Extraction Tool"
    description: str = "Extracts structured financial information from preprocessed email content. Handles task context data."
    
    def _run(self, clean_email_text: Any) -> str:
        """Extract financial entities from clean email text."""
        
        try:
            import json
            # Handle CrewAI task context input
            if isinstance(clean_email_text, str):
                try:
                    parsed_input = json.loads(clean_email_text)
                    if isinstance(parsed_input, list):
                        # Process list of cleaned emails
                        extracted_entities = []
                        for email_text in parsed_input:
                            entity = self._extract_from_single_email(email_text)
                            extracted_entities.append(entity)
                        return json.dumps(extracted_entities)
                except json.JSONDecodeError:
                    # Treat as single email text
                    return self._extract_from_single_email(clean_email_text)
            elif isinstance(clean_email_text, list):
                # List of email texts
                extracted_entities = []
                for email_text in clean_email_text:
                    entity = self._extract_from_single_email(email_text)
                    extracted_entities.append(entity)
                return json.dumps(extracted_entities)
            else:
                return f"Error: Unexpected input type - {type(clean_email_text)}"
                
        except Exception as e:
            logger.error(f"Error in entity extraction: {e}")
            return f"Error extracting entities: {str(e)}"
    
    def _extract_from_single_email(self, email_text: str) -> str:
        """Extract entities from a single email text."""
        
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
        {email_text}
        
        Return only valid JSON, no additional text.
        """
        
        # This would typically call an LLM like OpenAI GPT-4
        # For now, return the prompt that would be sent to the LLM
        return extraction_prompt


class SchemaValidationTool(BaseTool):
    """Tool for validating extracted entity data against schema."""
    
    name: str = "Schema Validation Tool"
    description: str = "Validates extracted financial entity data against predefined schema. Handles task context with multiple entities."
    
    def _run(self, extracted_data: Any) -> str:
        """Validate extracted entity data."""
        try:
            # Handle different input types from CrewAI task context
            if isinstance(extracted_data, str):
                if not extracted_data.strip():
                    return json.dumps({"valid": False, "errors": ["Empty data"]})
                try:
                    data = json.loads(extracted_data)
                except json.JSONDecodeError as e:
                    return json.dumps({"valid": False, "errors": [f"Invalid JSON: {str(e)}"]})
            elif isinstance(extracted_data, (dict, list)):
                data = extracted_data
            else:
                return json.dumps({"valid": False, "errors": [f"Unexpected input type: {type(extracted_data)}"]})
            
            # Handle list of entities
            if isinstance(data, list):
                validated_entities = []
                for entity in data:
                    validation_result = self._validate_single_entity(entity)
                    validated_entities.append(validation_result)
                return json.dumps({
                    "validated_entities": validated_entities,
                    "total_entities": len(data),
                    "valid_entities": len([e for e in validated_entities if e.get("valid", False)])
                })
            else:
                # Single entity validation
                return json.dumps(self._validate_single_entity(data))
                
        except Exception as e:
            logger.error(f"Error validating schema: {e}")
            return json.dumps({"valid": False, "errors": [f"Validation error: {str(e)}"]})
    
    def _validate_single_entity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single entity."""
        try:
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
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating single entity: {e}")
            return {"valid": False, "errors": [f"Validation error: {str(e)}"]}


class ClassificationTool(BaseTool):
    """Tool for classifying financial entities into categories."""
    
    name: str = "Entity Classification Tool"
    description: str = "Classifies financial entities and determines processing rules. Handles task context with multiple validated entities."
    
    def _run(self, validated_entity: Any) -> str:
        """Classify entity and determine processing rules."""
        try:
            # Handle different input types from CrewAI task context
            if isinstance(validated_entity, str):
                data = json.loads(validated_entity)
            elif isinstance(validated_entity, dict):
                # Handle validation result structure
                if 'validated_entities' in validated_entity:
                    # Multiple entities from validation task
                    classified_entities = []
                    for entity_result in validated_entity['validated_entities']:
                        if entity_result.get('valid', False):
                            classified = self._classify_single_entity(entity_result['validated_data'])
                            classified_entities.append(classified)
                    return json.dumps({
                        "classified_entities": classified_entities,
                        "total_classified": len(classified_entities)
                    })
                elif 'validated_data' in validated_entity:
                    # Single validated entity
                    data = validated_entity['validated_data']
                else:
                    # Direct entity data
                    data = validated_entity
            elif isinstance(validated_entity, list):
                # List of entities
                classified_entities = []
                for entity in validated_entity:
                    classified = self._classify_single_entity(entity)
                    classified_entities.append(classified)
                return json.dumps(classified_entities)
            else:
                return json.dumps({"classified": False, "error": f"Unexpected input type: {type(validated_entity)}"})
            
            # Single entity classification
            return json.dumps(self._classify_single_entity(data))
            
        except Exception as e:
            logger.error(f"Error classifying entity: {e}")
            return json.dumps({"classified": False, "error": str(e)})
    
    def _classify_single_entity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Classify a single entity."""
        try:
            
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
            
            return result
            
        except Exception as e:
            logger.error(f"Error classifying single entity: {e}")
            return {"classified": False, "error": str(e)}


class DeduplicationTool(BaseTool):
    """Tool for detecting and handling duplicate entities."""
    
    name: str = "Deduplication Tool"
    description: str = "Detects and handles duplicate financial entities. Handles task context with classified entities."

    def _run(self, entity_data: Any, existing_entities: Any = "[]") -> str:
        """Detect and merge duplicate financial entities."""
        try:
            # Handle different input types from CrewAI task context
            if isinstance(entity_data, str):
                try:
                    current_entities = json.loads(entity_data)
                except json.JSONDecodeError:
                    return json.dumps({"error": f"Invalid JSON in entity_data: {entity_data[:100]}"})
            else:
                current_entities = entity_data

            if isinstance(existing_entities, str):
                try:
                    existing_entities_list = json.loads(existing_entities)
                except json.JSONDecodeError:
                    existing_entities_list = []
            else:
                existing_entities_list = existing_entities

            if not isinstance(current_entities, list):
                current_entities = [current_entities]

            unique_entities = []
            duplicate_info = []

            for entity in current_entities:
                result = self._check_duplicates_single(entity, existing_entities_list + unique_entities)
                if not result["is_duplicate"]:
                    unique_entities.append(entity)
                else:
                    duplicate_info.append({
                        "entity": entity,
                        "duplicate_of": result["duplicate_of"]
                    })
            
            return json.dumps({
                "unique_entities": unique_entities,
                "duplicate_info": duplicate_info,
                "total_unique": len(unique_entities),
                "duplicates_found": len(duplicate_info)
            })

        except Exception as e:
            logger.error(f"Error in deduplication tool: {e}")
            return json.dumps({"error": str(e)})
    
    def _check_duplicates_single(self, current_entity: Dict[str, Any], existing_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check duplicates for a single entity."""
        try:
            
            duplicates = []
            
            for existing_entity in existing_entities:
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
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking duplicates for single entity: {e}")
            return {"is_duplicate": False, "error": str(e)}
    
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
    description: str = "Handles database operations for financial entities. Handles task context with deduplicated entities."

    def _run(self, operation: str, data: str = "") -> str:
        """Run database operations."""
        logger.info(f"DatabaseTool called with operation: {operation}")
        
        try:
            if operation == "query":
                # Dummy implementation for querying
                return json.dumps({"status": "success", "data": []})
            
            elif operation == "batch_insert":
                try:
                    entities = json.loads(data)
                    if not isinstance(entities, list):
                        return json.dumps({"error": "batch_insert expects a list of entities"})
                    
                    logger.info(f"Attempting to batch insert {len(entities)} entities.")
                    
                    # Dummy implementation for batch insert
                    stored_entities = []
                    for entity in entities:
                        stored_entity = {
                            **entity,
                            "entity_id": str(uuid.uuid4()),
                            "created_at": datetime.utcnow().isoformat(),
                            "status": "active"
                        }
                        stored_entities.append(stored_entity)
                    
                    return json.dumps({
                        "stored_entities": stored_entities,
                        "total_stored": len(stored_entities),
                        "processing_summary": {
                            "success": True,
                            "entities_processed": len(stored_entities),
                            "errors": []
                        }
                    })
                except json.JSONDecodeError:
                    return json.dumps({"error": "Invalid JSON format for data in batch_insert"})
                except Exception as e:
                    logger.error(f"Error during batch insert: {e}")
                    return json.dumps({"error": f"Batch insert failed: {str(e)}"})
            
            else:
                return json.dumps({"error": f"Unknown operation: {operation}"})
                
        except Exception as e:
            logger.error(f"Error in DatabaseTool: {e}")
            return json.dumps({"error": f"An unexpected error occurred: {str(e)}"})


# Export all tools
__all__ = [
    'EmailProcessingTool',
    'EntityExtractionTool', 
    'SchemaValidationTool',
    'ClassificationTool',
    'DeduplicationTool',
    'DatabaseTool'
] 