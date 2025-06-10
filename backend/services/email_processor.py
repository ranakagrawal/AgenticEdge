"""Main email processing service that orchestrates the complete pipeline."""

import asyncio
import json
import re
import os
from datetime import datetime, timezone
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
        
        logger.info(f"[CREWAI] Starting email processing run {run_id} for user {user_profile.user_id}")
        
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
            logger.info("[CREWAI] Step 2: Processing emails through CrewAI crew orchestration")
            processed_entities = await self._run_crewai_pipeline(emails, user_profile, run_id)
            processing_run.entities_extracted = len(processed_entities)
            
            # Step 3: Log results
            logger.info("Step 3: Logging processing results")
            await self._log_processing_results(run_id, processed_entities)
            
            # Mark run as completed
            processing_run.status = "completed"
            processing_run.completed_at = datetime.utcnow()
            
            logger.info(f"[CREWAI] Successfully completed processing run {run_id}")
            
            return self._create_processing_result(processing_run, processed_entities)
            
        except Exception as e:
            logger.error(f"Error in processing run {run_id}: {e}")
            processing_run.status = "failed"
            processing_run.completed_at = datetime.utcnow()
            processing_run.errors.append(str(e))
            
            # Enhanced error handling for different failure types
            error_details = self._categorize_processing_error(e)
            processing_run.error_category = error_details.get('category', 'unknown')
            processing_run.recovery_suggestions = error_details.get('suggestions', [])
            
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
    async def _run_crewai_pipeline(
        self, 
        emails: List[Dict[str, Any]], 
        user_profile: UserProfile, 
        run_id: str
    ) -> List[Dict[str, Any]]:
        """Process emails through CrewAI crew orchestration using crew.kickoff()."""
        
        try:
            logger.info(f"[CREWAI] Starting CrewAI pipeline for {len(emails)} emails")
            
            # Create the processing crew with all tasks and agents
            crew = self.agents_factory.create_processing_crew(
                user_profile=user_profile,
                days_back=180,  # This will be passed in task context
                max_emails=100  # This will be passed in task context
            )
            
            # Prepare input data for the crew
            crew_input = {
                "emails": emails,
                "user_profile": {
                    "user_id": user_profile.user_id,
                    "access_token": user_profile.access_token,
                    "refresh_token": user_profile.refresh_token
                },
                "run_id": run_id,
                "user_id": user_profile.user_id,
                "processing_params": {
                    "days_back": 180,
                    "max_emails": 100
                }
            }
            
            logger.info("[CREWAI] Executing crew kickoff with all tasks...")
            
            # Execute the crew with kickoff() - this runs all tasks in sequence
            result = crew.kickoff(inputs=crew_input)
            
            logger.info("[CREWAI] CrewAI crew execution completed successfully")
            
            # Parse the result to extract processed entities
            if isinstance(result, dict) and 'processed_entities' in result:
                processed_entities = result['processed_entities']
            else:
                # If result format is different, extract from the final task output
                processed_entities = self._extract_entities_from_crew_result(result, run_id)
            
            logger.info(f"[CREWAI] CrewAI pipeline processed {len(processed_entities)} entities")
            return processed_entities
            
        except Exception as e:
            logger.error(f"Error in CrewAI pipeline execution: {e}")
            # Fallback to manual processing if needed
            logger.warning("Falling back to manual processing due to CrewAI error")
            return await self._fallback_manual_processing(emails, user_profile.user_id)
    
    def _extract_entities_from_crew_result(self, crew_result, run_id: str) -> List[Dict[str, Any]]:
        """Extract processed entities from crew execution result."""
        try:
            logger.info(f"[CREWAI] Extracting entities from crew result: {type(crew_result)}")

            # Create a directory for agent outputs for this run
            output_dir = os.path.join(settings.log_dir, run_id, "agent_outputs")
            os.makedirs(output_dir, exist_ok=True)
            
            # CrewAI 0.55+ returns a CrewOutput object
            if hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
                # Get the task outputs - we want the store_entities_task output (second to last)
                task_outputs = crew_result.tasks_output
                logger.info(f"[CREWAI] Found {len(task_outputs)} task outputs")
                
                # Log all task outputs for debugging
                for i, task_output in enumerate(task_outputs):
                    agent_name = f"agent_{i}"
                    
                    # Debug: log the actual attributes of task_output
                    logger.info(f"[CREWAI] Task {i} attributes: {dir(task_output)}")
                    
                    try:
                        if hasattr(task_output, 'agent') and task_output.agent:
                            # Check if agent is an object with role attribute or just a string
                            if hasattr(task_output.agent, 'role'):
                                agent_name = task_output.agent.role.lower().replace(" ", "_")
                            elif isinstance(task_output.agent, str):
                                agent_name = task_output.agent.lower().replace(" ", "_")
                            else:
                                agent_name = str(task_output.agent).lower().replace(" ", "_")
                        elif hasattr(task_output, 'description') and task_output.description:
                            # Try to infer agent name from description
                            description = str(task_output.description).lower()
                            if "email fetcher" in description:
                                agent_name = "email_fetcher"
                            elif "preprocessor" in description:
                                agent_name = "email_preprocessor"
                            elif "entity extractor" in description:
                                agent_name = "financial_entity_extractor"
                            elif "validator" in description and "deduplicator" not in description:
                                agent_name = "data_validator"
                            elif "classifier" in description:
                                agent_name = "financial_classifier"
                            elif "deduplicator" in description:
                                agent_name = "validator_and_deduplicator"
                            elif "state updater" in description:
                                agent_name = "state_updater"
                            elif "notification" in description:
                                agent_name = "notification_manager"
                        
                        output_filename = os.path.join(output_dir, f"task_{i}_{agent_name}.json")
                        
                        output_content = {}
                        if hasattr(task_output, 'raw') and task_output.raw:
                            # Log a preview of the raw output
                            logger.info(f"[CREWAI] Task {i} output preview: {str(task_output.raw)[:200]}...")
                            # Try to parse as JSON, otherwise save as string
                            try:
                                output_content = json.loads(task_output.raw)
                            except (json.JSONDecodeError, TypeError):
                                output_content = {"raw_output": str(task_output.raw)}
                        elif hasattr(task_output, 'result') and task_output.result:
                            try:
                                output_content = json.loads(task_output.result)
                            except (json.JSONDecodeError, TypeError):
                                output_content = {"result_output": str(task_output.result)}
                        else:
                            output_content = {"output": str(task_output)}
                        
                        with open(output_filename, 'w') as f:
                            json.dump(output_content, f, indent=2)
                        
                        logger.info(f"Saved output for task {i} ({agent_name}) to {output_filename}")

                    except Exception as e:
                        logger.error(f"Could not save output for task {i} ({agent_name}): {e}")
                        # Still try to save something even if there's an error
                        try:
                            fallback_filename = os.path.join(output_dir, f"task_{i}_error.json")
                            with open(fallback_filename, 'w') as f:
                                json.dump({
                                    "error": str(e),
                                    "task_output_str": str(task_output),
                                    "task_attributes": dir(task_output) if hasattr(task_output, '__dict__') else "no attributes"
                                }, f, indent=2)
                            logger.info(f"Saved error output to {fallback_filename}")
                        except Exception as fallback_error:
                            logger.error(f"Could not even save error output: {fallback_error}")


                # Strategy 1: Try to get the store entities task output (index -2, before notification task)
                if len(task_outputs) >= 2:
                    store_task_output = task_outputs[-2]  # Second to last task (store entities)
                    logger.info(f"[CREWAI] Store task output type: {type(store_task_output)}")
                    
                    entities = self._try_extract_json_entities(store_task_output, "store_task")
                    if entities:
                        logger.info(f"[CREWAI] Successfully extracted {len(entities)} entities from store task")
                        return entities
                
                # Strategy 2: Try deduplication task (index -3)
                if len(task_outputs) >= 3:
                    dedup_task_output = task_outputs[-3]  # Third to last task (deduplication)
                    entities = self._try_extract_json_entities(dedup_task_output, "dedup_task")
                    if entities:
                        logger.info(f"[CREWAI] Successfully extracted {len(entities)} entities from dedup task")
                        return entities
                
                # Strategy 3: Try classification task (index -4)
                if len(task_outputs) >= 4:
                    classify_task_output = task_outputs[-4]  # Fourth to last task (classification)
                    entities = self._try_extract_json_entities(classify_task_output, "classify_task")
                    if entities:
                        logger.info(f"[CREWAI] Successfully extracted {len(entities)} entities from classify task")
                        return entities
                
                # Strategy 4: Scan all task outputs for entity-like data
                logger.info("[CREWAI] Scanning all task outputs for entity data...")
                for i, task_output in enumerate(task_outputs):
                    entities = self._try_extract_json_entities(task_output, f"task_{i}")
                    if entities:
                        logger.info(f"[CREWAI] Successfully extracted {len(entities)} entities from task {i}")
                        return entities
            
            # Fallback to trying the main result object
            if hasattr(crew_result, 'raw') and isinstance(crew_result.raw, str):
                entities = self._try_extract_json_entities(crew_result, "main_result")
                if entities:
                    logger.info(f"[CREWAI] Successfully extracted {len(entities)} entities from main result")
                    return entities
            
            # Direct result checks
            if isinstance(crew_result, dict):
                entities = self._extract_entities_from_dict(crew_result)
                if entities:
                    logger.info(f"[CREWAI] Successfully extracted {len(entities)} entities from result dict")
                    return entities
            elif isinstance(crew_result, list):
                if all(isinstance(item, dict) for item in crew_result):
                    logger.info(f"[CREWAI] Found entity list directly in result: {len(crew_result)} entities")
                    return crew_result
            
            logger.warning("[CREWAI] Could not extract entities from crew result, returning empty list")
            return []
            
        except Exception as e:
            logger.error(f"Error extracting entities from crew result: {e}")
            return []
    
    def _try_extract_json_entities(self, task_output, source_name: str) -> List[Dict[str, Any]]:
        """Try to extract entities from a task output as JSON."""
        try:
            if not hasattr(task_output, 'raw') or not task_output.raw:
                return []
            
            raw_text = task_output.raw.strip()
            if not raw_text:
                return []
            
            # Try to parse as JSON
            try:
                import json
                result_data = json.loads(raw_text)
                logger.info(f"[CREWAI] Parsed {source_name} JSON: {type(result_data)}")
                
                return self._extract_entities_from_dict(result_data)
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"[CREWAI] Could not parse {source_name} as JSON: {e}")
                
                # Try to extract JSON from text that might contain other content
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match:
                    try:
                        result_data = json.loads(json_match.group())
                        return self._extract_entities_from_dict(result_data)
                    except (json.JSONDecodeError, ValueError):
                        pass
                
                # Try to extract JSON array
                json_array_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                if json_array_match:
                    try:
                        result_data = json.loads(json_array_match.group())
                        if isinstance(result_data, list) and all(isinstance(item, dict) for item in result_data):
                            return result_data
                    except (json.JSONDecodeError, ValueError):
                        pass
                
                return []
        
        except Exception as e:
            logger.debug(f"Error extracting from {source_name}: {e}")
            return []
    
    def _extract_entities_from_dict(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract entities from a dictionary structure."""
        if isinstance(data, list):
            # If it's already a list of entities
            if all(isinstance(item, dict) for item in data):
                return data
        elif isinstance(data, dict):
            # Try different keys that might contain entities
            for key in ['stored_entities', 'unique_entities', 'processed_entities', 'entities', 'classified_entities', 'validated_entities']:
                if key in data and isinstance(data[key], list):
                    entities = data[key]
                    # Extract entity data if it's nested
                    clean_entities = []
                    for entity in entities:
                        if isinstance(entity, dict):
                            # Handle nested structure like {"data": {...}, "entity_id": "..."}
                            if 'data' in entity and isinstance(entity['data'], dict):
                                clean_entities.append(entity['data'])
                            # Handle entity with metadata
                            elif any(field in entity for field in ['merchant', 'amount', 'entity_type']):
                                clean_entities.append(entity)
                            # Handle classified entity structure
                            elif 'entity_data' in entity:
                                clean_entities.append(entity['entity_data'])
                            else:
                                clean_entities.append(entity)
                    return clean_entities
        
        return []
    
    async def _fallback_manual_processing(
        self, 
        emails: List[Dict[str, Any]], 
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Fallback manual processing if CrewAI fails."""
        
        logger.info("Using fallback manual processing")
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
    
    def _categorize_processing_error(self, error: Exception) -> Dict[str, Any]:
        """Categorize processing errors and provide recovery suggestions."""
        
        error_str = str(error).lower()
        
        if "gmail" in error_str or "authentication" in error_str:
            return {
                "category": "gmail_auth_error",
                "suggestions": [
                    "Check Gmail credentials",
                    "Refresh access token",
                    "Re-authorize Gmail access"
                ]
            }
        elif "crewai" in error_str or "crew" in error_str:
            return {
                "category": "crewai_execution_error",
                "suggestions": [
                    "Check agent configuration",
                    "Verify task dependencies",
                    "Review LLM API limits",
                    "Use fallback manual processing"
                ]
            }
        elif "validation" in error_str or "schema" in error_str:
            return {
                "category": "data_validation_error",
                "suggestions": [
                    "Review entity extraction logic",
                    "Check schema definitions",
                    "Validate input data format"
                ]
            }
        elif "timeout" in error_str or "execution" in error_str:
            return {
                "category": "timeout_error",
                "suggestions": [
                    "Reduce batch size",
                    "Increase timeout limits",
                    "Process emails in smaller chunks"
                ]
            }
        else:
            return {
                "category": "general_error",
                "suggestions": [
                    "Check system logs",
                    "Verify service dependencies",
                    "Retry processing"
                ]
            }
    
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