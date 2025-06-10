"""CrewAI agents for finance email processing pipeline."""

import uuid
from datetime import datetime
from typing import List, Dict, Any

from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from loguru import logger

from backend.config import settings
from backend.agents.tools import (
    EmailProcessingTool,
    EntityExtractionTool,
    SchemaValidationTool,
    ClassificationTool,
    DeduplicationTool,
    DatabaseTool
)
from backend.agents.finance_tasks import FinanceProcessingTasks


class FinanceProcessingAgents:
    """Factory class for creating finance processing agents."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.crewai_temperature,
            openai_api_key=settings.openai_api_key,
            max_tokens=settings.llm_max_tokens,
            request_timeout=settings.llm_request_timeout
        )
        
        # Initialize tools
        self.email_processing_tool = EmailProcessingTool()
        self.entity_extraction_tool = EntityExtractionTool()
        self.schema_validation_tool = SchemaValidationTool()
        self.classification_tool = ClassificationTool()
        self.deduplication_tool = DeduplicationTool()
        self.database_tool = DatabaseTool()
        
        # Initialize tasks factory
        self.tasks_factory = FinanceProcessingTasks(self)
    
    def create_supervisor_agent(self) -> Agent:
        """Create supervisor agent to orchestrate the pipeline."""
        return Agent(
            role='Processing Supervisor',
            goal='Orchestrate the email processing pipeline and ensure all steps complete successfully',
            backstory="""You are an experienced financial data processing supervisor who ensures 
                        that emails are processed through the complete pipeline with proper error 
                        handling and quality control. You coordinate between different agents and 
                        track overall progress.""",
            verbose=True,
            allow_delegation=True,
            llm=self.llm,
            tools=[]
        )
    
    def create_email_fetcher_agent(self) -> Agent:
        """Create agent responsible for fetching emails from Gmail."""
        return Agent(
            role='Email Fetcher',
            goal='Fetch financial emails from Gmail and prepare them for processing',
            backstory="""You are a specialized email retrieval expert who knows how to efficiently 
                        fetch financial emails from Gmail accounts. You understand financial email 
                        patterns and can filter relevant messages effectively.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[]
        )
    
    def create_processing_crew(self, user_profile, days_back: int = 180, max_emails: int = 100) -> Crew:
        """Create and configure the complete processing crew with tasks."""
        
        # Create all tasks with dependencies
        tasks = self.tasks_factory.create_task_workflow(user_profile, days_back, max_emails)
        
        # Create all agents (they're already assigned to tasks)
        agents = [
            self.create_email_fetcher_agent(),
            self.create_preprocessor_agent(),
            self.create_entity_extractor_agent(),
            self.create_schema_validator_agent(),
            self.create_classifier_agent(),
            self.create_validator_deduplicator_agent(),
            self.create_state_updater_agent(),
            self.create_notifier_agent()
        ]
        
        # Create crew with sequential process
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=settings.crewai_verbose,
            memory=settings.crewai_memory,
            max_execution_time=settings.crewai_max_execution_time,
            max_iter=settings.crewai_max_iter
        )
        
        logger.info(f"Created processing crew with {len(agents)} agents and {len(tasks)} tasks")
        return crew
    
    def create_all_tasks(self, user_profile, days_back: int = 180, max_emails: int = 100) -> List[Task]:
        """Create all tasks for the processing workflow."""
        return self.tasks_factory.create_task_workflow(user_profile, days_back, max_emails)
    
    def create_preprocessor_agent(self) -> Agent:
        """Create agent for email preprocessing and cleaning."""
        return Agent(
            role='Email Preprocessor',
            goal='Clean and prepare email content for optimal LLM processing',
            backstory="""You are an expert in email content processing who specializes in cleaning 
                        and structuring email data. You remove noise, extract relevant content, 
                        and format emails for downstream processing.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[self.email_processing_tool]
        )
    
    def create_entity_extractor_agent(self) -> Agent:
        """Create agent for extracting financial entities using LLM."""
        return Agent(
            role='Financial Entity Extractor',
            goal='Extract structured financial information from email content with high accuracy',
            backstory="""You are a financial data extraction expert specializing in Indian financial 
                        systems. You understand various types of financial communications including 
                        subscription renewals, bill statements, loan EMIs, and payment notifications. 
                        You can accurately identify amounts, due dates, merchants, and payment types.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[self.entity_extraction_tool]
        )
    
    def create_schema_validator_agent(self) -> Agent:
        """Create agent for validating extracted data against schema."""
        return Agent(
            role='Data Validator',
            goal='Ensure extracted financial data meets quality standards and schema requirements',
            backstory="""You are a meticulous data quality expert who ensures that extracted 
                        financial information is accurate, complete, and follows the required 
                        schema. You catch errors and inconsistencies before they enter the system.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[self.schema_validation_tool]
        )
    
    def create_classifier_agent(self) -> Agent:
        """Create agent for classifying financial entities."""
        return Agent(
            role='Financial Classifier',
            goal='Classify financial entities into appropriate categories and determine processing rules',
            backstory="""You are a financial categorization specialist who understands different 
                        types of financial obligations. You can distinguish between subscriptions, 
                        bills, and loans, and assign appropriate categories and processing rules.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[self.classification_tool]
        )
    
    def create_validator_deduplicator_agent(self) -> Agent:
        """Create agent for validation and deduplication."""
        return Agent(
            role='Validator and Deduplicator',
            goal='Remove duplicate entries and perform final validation before storage',
            backstory="""You are an expert in data integrity who ensures no duplicate financial 
                        entries exist in the system. You can identify various forms of duplicates 
                        and make intelligent decisions about data consolidation.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[self.deduplication_tool]
        )
    
    def create_state_updater_agent(self) -> Agent:
        """Create agent for updating database state."""
        return Agent(
            role='State Updater',
            goal='Persist validated financial entities to the database efficiently',
            backstory="""You are a database operations specialist who ensures that validated 
                        financial data is properly stored and indexed. You handle transactions 
                        and maintain data consistency.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[self.database_tool]
        )
    
    def create_notifier_agent(self) -> Agent:
        """Create agent for handling notifications and logging."""
        return Agent(
            role='Notification Manager',
            goal='Generate appropriate notifications and maintain processing logs',
            backstory="""You are a communication specialist who ensures users and systems are 
                        properly notified about processing results. You generate logs, alerts, 
                        and user notifications as needed.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[]
        ) 