"""CrewAI task definitions for finance email processing pipeline."""

from typing import List, Dict, Any
from crewai import Task
from loguru import logger


class FinanceProcessingTasks:
    """Factory class for creating finance processing tasks."""
    
    def __init__(self, agents_factory):
        """Initialize with reference to agents factory."""
        self.agents_factory = agents_factory
    
    def create_fetch_emails_task(self, user_profile, days_back: int = 180, max_emails: int = 100) -> Task:
        """Create task for fetching emails from Gmail."""
        return Task(
            description=f"""
            Fetch financial emails from Gmail for user {user_profile.user_id}.
            
            Parameters:
            - Days back: {days_back}
            - Max emails: {max_emails}
            - User has valid access_token: {bool(user_profile.access_token)}
            - User has valid refresh_token: {bool(user_profile.refresh_token)}
            
            Requirements:
            1. Use the user's Gmail credentials to fetch emails
            2. Focus on financial emails (bills, subscriptions, payment notifications)
            3. Return emails in structured format with message_id, subject, body, from, date
            4. Handle authentication errors gracefully
            5. Log the number of emails fetched
            
            Expected output: List of email dictionaries with required fields
            """,
            agent=self.agents_factory.create_email_fetcher_agent(),
            expected_output="List of email dictionaries containing message_id, subject, body, from, and date fields",
            context=[]  # No dependencies
        )
    
    def create_preprocess_emails_task(self, fetch_emails_task: Task) -> Task:
        """Create task for preprocessing emails."""
        return Task(
            description="""
            Clean and preprocess the fetched emails for optimal LLM processing.
            
            Requirements:
            1. Remove HTML tags from email bodies
            2. Clean excessive whitespace and formatting
            3. Remove email noise (unsubscribe links, footers, etc.)
            4. Extract relevant content (subject, sender, main body)
            5. Prepare clean text for entity extraction
            6. Preserve important financial information
            
            For each email, create a clean, structured text format that highlights:
            - Email subject
            - Sender information  
            - Main content (limited to relevant portions)
            
            Expected output: List of preprocessed email texts ready for entity extraction
            """,
            agent=self.agents_factory.create_preprocessor_agent(),
            expected_output="List of cleaned email texts with preserved financial information",
            context=[fetch_emails_task]
        )
    
    def create_extract_entities_task(self, preprocess_emails_task: Task) -> Task:
        """Create task for extracting financial entities."""
        return Task(
            description="""
            Extract structured financial information from preprocessed emails using LLM.
            
            For each email, extract the following information:
            - merchant: Service provider/merchant name
            - amount: Payment amount (numeric)
            - currency: Currency code (usually INR)
            - due_date: Payment due date (YYYY-MM-DD format)
            - entity_type: subscription|bill|loan
            - category: Appropriate category based on merchant/service
            - auto_debit: Whether auto-debit is enabled
            - billing_cycle: For subscriptions (monthly|quarterly|yearly|one-time)
            - principal_amount: For loans only
            - interest_amount: For loans only
            - late_fee: If mentioned in email
            - confidence_score: Extraction confidence (0.0-1.0)
            
            Focus on Indian financial systems and patterns. Handle various formats
            of amounts (₹, Rs., INR) and date formats commonly used in India.
            
            Expected output: List of extracted financial entity dictionaries
            """,
            agent=self.agents_factory.create_entity_extractor_agent(),
            expected_output="List of structured financial entity dictionaries with all required fields",
            context=[preprocess_emails_task]
        )
    
    def create_validate_entities_task(self, extract_entities_task: Task) -> Task:
        """Create task for validating extracted entities."""
        return Task(
            description="""
            Validate extracted financial entities against schema requirements.
            
            Validation criteria:
            1. Required fields: merchant, amount, entity_type, category
            2. Amount must be positive numeric value
            3. Due date must be valid date in YYYY-MM-DD format
            4. Entity type must be: subscription|bill|loan
            5. Category must be valid predefined category
            6. Confidence score must be between 0.0-1.0
            7. Auto debit must be boolean
            8. For loans: validate principal_amount and interest_amount
            
            For each entity:
            - Check all validation rules
            - Flag any validation errors
            - Return validation result with errors (if any)
            - Only pass entities that meet all validation criteria
            
            Expected output: List of validated entities with validation status
            """,
            agent=self.agents_factory.create_schema_validator_agent(),
            expected_output="List of validation results indicating which entities passed validation",
            context=[extract_entities_task]
        )
    
    def create_classify_entities_task(self, validate_entities_task: Task) -> Task:
        """Create task for classifying entities and determining processing rules."""
        return Task(
            description="""
            Classify validated financial entities and determine processing rules.
            
            Classification tasks:
            1. Refine entity categories based on merchant and content analysis
            2. Determine urgency level based on due dates
            3. Set priority scores for payment scheduling
            4. Identify recurring vs one-time payments
            5. Flag high-risk or suspicious transactions
            6. Assign processing rules and recommendations
            
            For each entity, add:
            - refined_category: More specific category if possible
            - urgency_level: low|medium|high|critical
            - priority_score: 1-10 based on due date and importance
            - is_recurring: boolean for recurring payments
            - risk_level: low|medium|high
            - processing_recommendations: List of suggested actions
            - payment_window: Days until due date
            
            Expected output: List of classified entities with processing metadata
            """,
            agent=self.agents_factory.create_classifier_agent(),
            expected_output="List of classified entities with urgency levels and processing recommendations",
            context=[validate_entities_task]
        )
    
    def create_deduplicate_entities_task(self, classify_entities_task: Task) -> Task:
        """Create task for removing duplicate entities."""
        return Task(
            description="""
            Remove duplicate financial entities and consolidate similar entries.
            
            Deduplication logic:
            1. Compare entities by merchant, amount, and due date
            2. Handle variations in merchant names (fuzzy matching)
            3. Identify recurring payment updates vs duplicates
            4. Merge complementary information from similar entities
            5. Preserve the most complete and recent entity data
            6. Track deduplication actions for audit trail
            
            For duplicate detection, consider:
            - Exact matches (merchant + amount + due date)
            - Fuzzy merchant name matches with same amount
            - Recurring payments with updated information
            - Split transactions that should be combined
            
            IMPORTANT: You must return your result as valid JSON in this exact format:
            {
                "unique_entities": [list of deduplicated entities],
                "duplicate_info": [list of duplicate summaries],
                "total_unique": number,
                "duplicates_found": number
            }
            
            Expected output: JSON object containing deduplicated list of unique financial entities
            """,
            agent=self.agents_factory.create_validator_deduplicator_agent(),
            expected_output="JSON object with unique_entities array, duplicate_info, total_unique count, and duplicates_found count",
            context=[classify_entities_task]
        )
    
    def create_store_entities_task(self, deduplicate_entities_task: Task) -> Task:
        """Create task for storing validated entities to database."""
        return Task(
            description="""
            Store the unique financial entities from the previous step to the database.

            You must use the 'batch_insert' operation of the 'Database Tool'.
            The 'data' parameter for the tool must be a JSON string representation
            of the list of unique entities.

            Steps:
            1. Get the 'unique_entities' list from the context.
            2. Call the 'Database Tool' with:
               - operation='batch_insert'
               - data=JSON.stringify(unique_entities)
            3. Ensure the output is a JSON object confirming the storage operation.

            IMPORTANT: You must return your result as valid JSON in this exact format:
            {
                "stored_entities": [list of stored entities with metadata],
                "total_stored": number,
                "processing_summary": {
                    "success": true/false,
                    "entities_processed": number,
                    "errors": []
                }
            }
            """,
            agent=self.agents_factory.create_state_updater_agent(),
            expected_output="JSON object with stored_entities array, total_stored count, and processing_summary",
            context=[deduplicate_entities_task]
        )
    
    def create_notify_completion_task(self, store_entities_task: Task) -> Task:
        """Create task for handling notifications and final logging."""
        return Task(
            description="""
            Generate completion notifications and finalize processing logs.
            
            Notification tasks:
            1. Create processing summary report
            2. Log final statistics (entities processed, stored, errors)
            3. Generate user notifications for important findings
            4. Create alerts for urgent payment due dates
            5. Update processing run status to 'completed'
            6. Archive processing artifacts
            
            Summary should include:
            - Total emails processed
            - Entities extracted and stored
            - Processing errors and warnings
            - Urgent payments identified
            - Processing duration and performance metrics
            - Recommendations for user action
            
            Expected output: Processing completion summary with notifications sent
            """,
            agent=self.agents_factory.create_notifier_agent(),
            expected_output="Processing completion summary with notification status and final statistics",
            context=[store_entities_task]
        )
    
    def create_task_workflow(self, user_profile, days_back: int = 180, max_emails: int = 100) -> List[Task]:
        """Create the complete task workflow with proper dependencies."""
        
        # Create tasks in dependency order
        fetch_task = self.create_fetch_emails_task(user_profile, days_back, max_emails)
        preprocess_task = self.create_preprocess_emails_task(fetch_task)
        extract_task = self.create_extract_entities_task(preprocess_task)
        validate_task = self.create_validate_entities_task(extract_task)
        classify_task = self.create_classify_entities_task(validate_task)
        deduplicate_task = self.create_deduplicate_entities_task(classify_task)
        store_task = self.create_store_entities_task(deduplicate_task)
        notify_task = self.create_notify_completion_task(store_task)
        
        # Return tasks in execution order
        return [
            fetch_task,
            preprocess_task,
            extract_task,
            validate_task,
            classify_task,
            deduplicate_task,
            store_task,
            notify_task
        ] 