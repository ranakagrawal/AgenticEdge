"""Main email processing service that orchestrates the complete pipeline."""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger

from backend.services.gmail_service import GmailService
from backend.agents.finance_agents import FinanceProcessingAgents
from backend.models.entities import UserProfile, ProcessingRun
from backend.config import settings


class EmailProcessingService:
    """Main service for processing financial emails through the complete pipeline."""
    
    def __init__(self):
        self.gmail_service = GmailService()
        self.agents_factory = FinanceProcessingAgents()
        
    async def process_user_emails(
        self, 
        user_profile: UserProfile,
        days_back: int = 180,
        max_emails: int = 100
    ) -> Dict[str, Any]:
        """Process financial emails for a user through the complete pipeline."""
        
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_profile.user_id[:8]}"
        
        # Create processing run record
        processing_run = ProcessingRun(
            run_id=run_id,
            user_id=user_profile.user_id,
            started_at=datetime.utcnow(),
            status="running"
        )
        
        logger.info(f"Starting email processing run {run_id} for user {user_profile.user_id}")
        
        try:
            # Step 1: Fetch emails from Gmail
            logger.info("Step 1: Fetching emails from Gmail")
            emails = await self._fetch_emails(user_profile, days_back, max_emails)
            processing_run.emails_processed = len(emails)
            
            if not emails:
                logger.warning("No financial emails found for processing")
                processing_run.status = "completed"
                processing_run.completed_at = datetime.utcnow()
                return self._create_processing_result(processing_run, [])
            
            logger.info(f"Fetched {len(emails)} emails for processing")
            
            # Step 2: Process emails through CrewAI pipeline
            logger.info("Step 2: Processing emails through AI pipeline")
            processed_entities = await self._process_emails_with_crew(emails, user_profile.user_id)
            processing_run.entities_extracted = len(processed_entities)
            
            # Step 3: Log results
            logger.info("Step 3: Logging processing results")
            await self._log_processing_results(run_id, processed_entities)
            
            # Mark run as completed
            processing_run.status = "completed"
            processing_run.completed_at = datetime.utcnow()
            
            logger.info(f"Successfully completed processing run {run_id}")
            
            return self._create_processing_result(processing_run, processed_entities)
            
        except Exception as e:
            logger.error(f"Error in processing run {run_id}: {e}")
            processing_run.status = "failed"
            processing_run.completed_at = datetime.utcnow()
            processing_run.errors.append(str(e))
            
            return self._create_processing_result(processing_run, [], error=str(e))
    
    async def _fetch_emails(
        self, 
        user_profile: UserProfile, 
        days_back: int, 
        max_emails: int
    ) -> List[Dict[str, Any]]:
        """Fetch emails from Gmail using the user's credentials."""
        
        logger.info(f"_fetch_emails function called for user {user_profile.user_id}")
        logger.info(f"Parameters: days_back={days_back}, max_emails={max_emails}")
        
        if not user_profile.access_token or not user_profile.refresh_token:
            logger.error("User does not have valid Gmail credentials")
            raise ValueError("User does not have valid Gmail credentials")
        
        try:
            logger.info("Calling Gmail service to fetch financial emails...")
            
            # Use Gmail service to fetch emails
            emails = self.gmail_service.get_financial_emails(
                access_token=user_profile.access_token,
                refresh_token=user_profile.refresh_token,
                days_back=days_back,
                max_results=max_emails
            )

            logger.info(f"Successfully fetched {len(emails)} emails from Gmail")
            logger.info(f"Fetched emails data: {emails}")
            
            return emails

            
            
        except Exception as e:
            logger.error(f"Error fetching emails for user {user_profile.user_id}: {e}")
            raise
    async def _process_emails_with_crew(
        self, 
        emails: List[Dict[str, Any]], 
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Process emails through the CrewAI agent pipeline."""
        
        processed_entities = []
        
        for email_data in emails:
            try:
                logger.info(f"Processing email: {email_data.get('message_id', 'unknown')}")
                
                # Step 1: Preprocess email
                processed_email = await self._preprocess_email(email_data)
                
                # Step 2: Extract entities using LLM
                extracted_entity = await self._extract_entity(processed_email)
                
                # Step 3: Validate extracted data
                validated_entity = await self._validate_entity(extracted_entity)
                
                # Step 4: Classify entity
                classified_entity = await self._classify_entity(validated_entity)
                
                # Step 5: Check for duplicates
                final_entity = await self._deduplicate_entity(classified_entity, processed_entities)
                
                if final_entity and final_entity.get('action') == 'process':
                    # Step 6: Add metadata
                    entity_with_metadata = self._add_processing_metadata(
                        final_entity['entity_data'], 
                        email_data, 
                        user_id
                    )
                    processed_entities.append(entity_with_metadata)
                    
                    logger.info(f"Successfully processed entity: {entity_with_metadata.get('merchant', 'unknown')}")
                
            except Exception as e:
                logger.error(f"Error processing email {email_data.get('message_id', 'unknown')}: {e}")
                continue
        
        return processed_entities
    
    async def _preprocess_email(self, email_data: Dict[str, Any]) -> str:
        """Preprocess email using the preprocessing tool."""
        
        try:
            # Create preprocessing agent
            preprocessor = self.agents_factory.create_preprocessor_agent()
            
            # Use the email processing tool directly
            tool = self.agents_factory.email_processing_tool
            clean_content = tool._run(email_data)
            
            return clean_content
            
        except Exception as e:
            logger.error(f"Error preprocessing email: {e}")
            raise
    
    async def _extract_entity(self, clean_email_content: str) -> Dict[str, Any]:
        """Extract financial entity from clean email content."""
        
        try:
            # Create entity extraction agent
            extractor = self.agents_factory.create_entity_extractor_agent()
            
            # Use the entity extraction tool to create prompt
            tool = self.agents_factory.entity_extraction_tool
            extraction_prompt = tool._run(clean_email_content)
            
            # In a real implementation, this would call the LLM with the prompt
            # For now, simulate LLM response with a basic parser
            extracted_data = self._simulate_llm_extraction(clean_email_content)
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting entity: {e}")
            raise
    
    async def _validate_entity(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extracted entity data."""
        
        try:
            # Use validation tool
            tool = self.agents_factory.schema_validation_tool
            validation_result = tool._run(json.dumps(extracted_data))
            
            validation_data = json.loads(validation_result)
            
            if not validation_data.get('valid', False):
                logger.warning(f"Validation failed: {validation_data.get('errors', [])}")
                raise ValueError(f"Validation errors: {validation_data.get('errors', [])}")
            
            return validation_data['validated_data']
            
        except Exception as e:
            logger.error(f"Error validating entity: {e}")
            raise
    
    async def _classify_entity(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Classify and enhance entity data."""
        
        try:
            # Use classification tool
            tool = self.agents_factory.classification_tool
            classification_result = tool._run(json.dumps(validated_data))
            
            classification_data = json.loads(classification_result)
            
            if not classification_data.get('classified', False):
                logger.warning(f"Classification failed: {classification_data.get('error', 'Unknown error')}")
                raise ValueError(f"Classification error: {classification_data.get('error', 'Unknown error')}")
            
            return classification_data['entity_data']
            
        except Exception as e:
            logger.error(f"Error classifying entity: {e}")
            raise
    
    async def _deduplicate_entity(
        self, 
        entity_data: Dict[str, Any], 
        existing_entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check for duplicates and handle them."""
        
        try:
            # Use deduplication tool
            tool = self.agents_factory.deduplication_tool
            dedup_result = tool._run(
                json.dumps(entity_data), 
                json.dumps(existing_entities)
            )
            
            return json.loads(dedup_result)
            
        except Exception as e:
            logger.error(f"Error checking duplicates: {e}")
            raise
    
    def _add_processing_metadata(
        self, 
        entity_data: Dict[str, Any], 
        email_data: Dict[str, Any], 
        user_id: str
    ) -> Dict[str, Any]:
        """Add processing metadata to entity."""
        
        entity_data.update({
            'user_id': user_id,
            'email_source': email_data.get('message_id', ''),
            'extracted_at': datetime.utcnow().isoformat(),
            'processing_version': '1.0'
        })
        
        return entity_data
    
    async def _log_processing_results(
        self, 
        run_id: str, 
        processed_entities: List[Dict[str, Any]]
    ) -> None:
        """Log processing results in structured format."""
        
        # Create comprehensive log entry
        log_entry = {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "entities_processed": len(processed_entities),
            "entities": processed_entities,
            "summary": {
                "subscriptions": len([e for e in processed_entities if e.get('entity_type') == 'subscription']),
                "bills": len([e for e in processed_entities if e.get('entity_type') == 'bill']),
                "loans": len([e for e in processed_entities if e.get('entity_type') == 'loan']),
                "total_amount": sum(float(e.get('amount', 0)) for e in processed_entities),
                "currency": "INR"
            }
        }
        
        # Log to file and console
        logger.info(f"PROCESSING RESULTS: {json.dumps(log_entry, indent=2)}")
        
        # Save to logs directory
        log_filename = f"logs/processing_{run_id}.json"
        try:
            import os
            os.makedirs("logs", exist_ok=True)
            with open(log_filename, 'w') as f:
                json.dump(log_entry, f, indent=2)
            logger.info(f"Processing results saved to {log_filename}")
        except Exception as e:
            logger.error(f"Error saving log file: {e}")
    
    def _create_processing_result(
        self, 
        processing_run: ProcessingRun, 
        entities: List[Dict[str, Any]], 
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create standardized processing result."""
        
        return {
            "run_id": processing_run.run_id,
            "user_id": processing_run.user_id,
            "status": processing_run.status,
            "started_at": processing_run.started_at.isoformat(),
            "completed_at": processing_run.completed_at.isoformat() if processing_run.completed_at else None,
            "emails_processed": processing_run.emails_processed,
            "entities_extracted": processing_run.entities_extracted,
            "entities": entities,
            "errors": processing_run.errors + ([error] if error else []),
            "summary": {
                "total_entities": len(entities),
                "by_type": {
                    "subscriptions": len([e for e in entities if e.get('entity_type') == 'subscription']),
                    "bills": len([e for e in entities if e.get('entity_type') == 'bill']),
                    "loans": len([e for e in entities if e.get('entity_type') == 'loan'])
                },
                "total_amount": sum(float(e.get('amount', 0)) for e in entities)
            }
        }
    
    def _simulate_llm_extraction(self, clean_email_content: str) -> Dict[str, Any]:
        """Simulate LLM extraction for testing purposes."""
        
        # This is a basic simulation - in production, this would call OpenAI GPT-4
        # Extract basic patterns from email content
        
        import re
        
        # Basic amount extraction
        amount_match = re.search(r'(?:₹|Rs\.?|INR)\s*(\d+(?:,\d+)*(?:\.\d{2})?)', clean_email_content)
        amount = float(amount_match.group(1).replace(',', '')) if amount_match else 100.0
        
        # Basic merchant extraction
        merchant = "Unknown Merchant"
        if "netflix" in clean_email_content.lower():
            merchant = "Netflix"
        elif "amazon" in clean_email_content.lower():
            merchant = "Amazon Prime"
        elif "hdfc" in clean_email_content.lower():
            merchant = "HDFC Bank"
        elif "icici" in clean_email_content.lower():
            merchant = "ICICI Bank"
        
        # Basic entity type detection
        entity_type = "bill"
        if any(keyword in clean_email_content.lower() for keyword in ["subscription", "renewal", "netflix", "prime"]):
            entity_type = "subscription"
        elif any(keyword in clean_email_content.lower() for keyword in ["emi", "loan", "installment"]):
            entity_type = "loan"
        
        # Basic category detection
        category = "miscellaneous"
        if entity_type == "subscription":
            category = "entertainment"
        elif "bank" in merchant.lower():
            category = "credit_card"
        
        # Simulate extracted data
        extracted_data = {
            "merchant": merchant,
            "amount": amount,
            "currency": "INR",
            "due_date": "2024-02-15",  # Mock date
            "entity_type": entity_type,
            "category": category,
            "auto_debit": True,
            "confidence_score": 0.8
        }
        
        return extracted_data 