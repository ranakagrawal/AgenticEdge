#!/usr/bin/env python3
"""
Test script for Finance Email Summarizer system components.
Tests the pipeline without requiring actual API keys.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
current_dir = Path(__file__).parent
env_path = current_dir / ".env"
load_dotenv(dotenv_path=env_path)

# Add the current directory to Python path
sys.path.insert(0, str(current_dir))

def test_models():
    """Test the data models."""
    print("🧪 Testing data models...")
    
    try:
        from backend.models.entities import PaymentEntity, UserProfile, EntityType, EntityCategory
        
        # Test PaymentEntity creation
        entity = PaymentEntity(
            email_source="test_msg_123",
            merchant="Netflix",
            amount=649.0,
            currency="INR",
            due_date=datetime(2024, 2, 15),
            entity_type=EntityType.SUBSCRIPTION,
            category=EntityCategory.ENTERTAINMENT,
            confidence_score=0.95,
            user_id="test_user_123"
        )
        
        print(f"✅ PaymentEntity created: {entity.merchant} - ₹{entity.amount}")
        
        # Test UserProfile creation
        profile = UserProfile(
            user_id="test_user_123",
            email="test@example.com",
            name="Test User"
        )
        
        print(f"✅ UserProfile created: {profile.name} ({profile.email})")
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False


def test_tools():
    """Test the agent tools."""
    print("\n🔧 Testing agent tools...")
    
    try:
        from backend.agents.tools import (
            EmailProcessingTool, 
            SchemaValidationTool,
            ClassificationTool,
            DeduplicationTool
        )
        
        # Test email preprocessing
        email_tool = EmailProcessingTool()
        test_email = {
            "subject": "Netflix Subscription Renewal",
            "body": "Your Netflix subscription of ₹649 will be charged on 15th Feb 2024",
            "from": "netflix@example.com"
        }
        
        clean_content = email_tool._run(test_email)
        print(f"✅ Email preprocessing: {len(clean_content)} characters cleaned")
        
        # Test schema validation
        validation_tool = SchemaValidationTool()
        test_data = {
            "merchant": "Netflix",
            "amount": 649.0,
            "entity_type": "subscription",
            "category": "entertainment",
            "confidence_score": 0.9
        }
        
        validation_result = validation_tool._run(json.dumps(test_data))
        result = json.loads(validation_result)
        print(f"✅ Schema validation: {result['valid']}")
        
        # Test classification
        classification_tool = ClassificationTool()
        classification_result = classification_tool._run(json.dumps(test_data))
        result = json.loads(classification_result)
        print(f"✅ Classification: {result['classified']}")
        
        # Test deduplication
        dedup_tool = DeduplicationTool()
        dedup_result = dedup_tool._run(json.dumps(test_data), "[]")
        result = json.loads(dedup_result)
        print(f"✅ Deduplication: {result['is_duplicate']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Tools test failed: {e}")
        return False


def test_email_simulation():
    """Test email processing simulation."""
    print("\n📧 Testing email processing simulation...")
    
    try:
        from backend.services.email_processor import EmailProcessingService
        
        processor = EmailProcessingService()
        
        # Test the simulation function
        test_content = """
        EMAIL SUBJECT: Netflix Subscription Renewal
        FROM: netflix@example.com
        CONTENT: Your Netflix subscription of ₹649 will be charged on 15th Feb 2024
        """
        
        extracted_data = processor._simulate_llm_extraction(test_content)
        print(f"✅ LLM simulation: {extracted_data['merchant']} - ₹{extracted_data['amount']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Email simulation test failed: {e}")
        return False


def test_config():
    """Test configuration loading."""
    print("\n⚙️ Testing configuration...")
    
    try:
        from backend.config import settings
        
        print(f"✅ Config loaded: {len(settings.gmail_scopes)} Gmail scopes configured")
        print(f"✅ MongoDB URL: {settings.mongodb_url}")
        print(f"✅ Database name: {settings.database_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False


def test_sample_processing():
    """Test complete processing flow with sample data."""
    print("\n🔄 Testing sample processing flow...")
    
    try:
        from backend.agents.tools import (
            EmailProcessingTool,
            SchemaValidationTool, 
            ClassificationTool
        )
        
        # Sample email data
        sample_email = {
            "message_id": "sample_123",
            "subject": "HDFC Credit Card Statement",
            "from": "hdfc@bank.com",
            "body": "Your HDFC Credit Card statement shows a balance of ₹12,500. Due date: 25th March 2024."
        }
        
        # Step 1: Preprocess
        email_tool = EmailProcessingTool()
        clean_content = email_tool._run(sample_email)
        print("✅ Step 1: Email preprocessed")
        
        # Step 2: Simulate extraction
        from backend.services.email_processor import EmailProcessingService
        processor = EmailProcessingService()
        extracted = processor._simulate_llm_extraction(clean_content)
        print(f"✅ Step 2: Entity extracted - {extracted['merchant']}")
        
        # Step 3: Validate
        validation_tool = SchemaValidationTool()
        validation_result = validation_tool._run(json.dumps(extracted))
        validation_data = json.loads(validation_result)
        print(f"✅ Step 3: Validation - {validation_data['valid']}")
        
        # Step 4: Classify
        if validation_data['valid']:
            classification_tool = ClassificationTool()
            classification_result = classification_tool._run(json.dumps(extracted))
            classification_data = json.loads(classification_result)
            print(f"✅ Step 4: Classification - {classification_data['classified']}")
        
        print("✅ Complete processing flow successful!")
        return True
        
    except Exception as e:
        print(f"❌ Sample processing test failed: {e}")
        return False


def test_crewai_agents():
    """Test CrewAI agent creation."""
    print("\n🤖 Testing CrewAI agents...")
    
    try:
        from backend.agents.finance_agents import FinanceProcessingAgents
        from backend.models.entities import UserProfile
        
        # Create agents factory
        agents_factory = FinanceProcessingAgents()
        print("✅ FinanceProcessingAgents factory created")
        
        # Test agent creation
        preprocessor = agents_factory.create_preprocessor_agent()
        print(f"✅ Preprocessor agent created: {preprocessor.role}")
        
        extractor = agents_factory.create_entity_extractor_agent()
        print(f"✅ Entity extractor agent created: {extractor.role}")
        
        validator = agents_factory.create_schema_validator_agent()
        print(f"✅ Validator agent created: {validator.role}")
        
        return True
        
    except Exception as e:
        print(f"❌ CrewAI agents test failed: {e}")
        return False


def test_crewai_tasks():
    """Test CrewAI task creation."""
    print("\n📋 Testing CrewAI tasks...")
    
    try:
        from backend.agents.finance_agents import FinanceProcessingAgents
        from backend.agents.finance_tasks import FinanceProcessingTasks
        from backend.models.entities import UserProfile
        
        # Create mock user profile
        user_profile = UserProfile(
            user_id="test_user_crewai",
            email="test@example.com",
            name="Test User",
            access_token="mock_token",
            refresh_token="mock_refresh"
        )
        
        # Create agents factory and tasks factory
        agents_factory = FinanceProcessingAgents()
        tasks_factory = FinanceProcessingTasks(agents_factory)
        print("✅ Tasks factory created")
        
        # Test task creation
        fetch_task = tasks_factory.create_fetch_emails_task(user_profile)
        print(f"✅ Fetch emails task created")
        
        preprocess_task = tasks_factory.create_preprocess_emails_task(fetch_task)
        print(f"✅ Preprocess emails task created")
        
        extract_task = tasks_factory.create_extract_entities_task(preprocess_task)
        print(f"✅ Extract entities task created")
        
        # Test complete workflow
        workflow = tasks_factory.create_task_workflow(user_profile)
        print(f"✅ Complete workflow created with {len(workflow)} tasks")
        
        return True
        
    except Exception as e:
        print(f"❌ CrewAI tasks test failed: {e}")
        return False


def test_crewai_crew_creation():
    """Test CrewAI crew creation."""
    print("\n👥 Testing CrewAI crew creation...")
    
    try:
        from backend.agents.finance_agents import FinanceProcessingAgents
        from backend.models.entities import UserProfile
        
        # Create mock user profile
        user_profile = UserProfile(
            user_id="test_user_crew",
            email="test@example.com", 
            name="Test User",
            access_token="mock_token",
            refresh_token="mock_refresh"
        )
        
        # Create agents factory
        agents_factory = FinanceProcessingAgents()
        
        # Test crew creation
        crew = agents_factory.create_processing_crew(user_profile)
        print(f"✅ Processing crew created with {len(crew.agents)} agents")
        print(f"✅ Crew has {len(crew.tasks)} tasks configured")
        print(f"✅ Crew process type: {crew.process}")
        
        return True
        
    except Exception as e:
        print(f"❌ CrewAI crew creation test failed: {e}")
        return False


def test_updated_tools_context():
    """Test updated tools with CrewAI context handling."""
    print("\n🔧 Testing updated tools with CrewAI context...")
    
    try:
        from backend.agents.tools import (
            EmailProcessingTool,
            EntityExtractionTool, 
            SchemaValidationTool,
            ClassificationTool,
            DeduplicationTool
        )
        
        # Test email preprocessing with list input (CrewAI context)
        email_tool = EmailProcessingTool()
        test_emails = [
            {
                "subject": "Netflix Subscription",
                "body": "Your Netflix subscription of ₹649 will be charged",
                "from": "netflix@example.com"
            },
            {
                "subject": "HDFC Credit Card",
                "body": "Your credit card bill of ₹12,500 is due on March 25",
                "from": "hdfc@bank.com"
            }
        ]
        
        # Test with list input
        result = email_tool._run(test_emails)
        import json
        parsed_result = json.loads(result)
        print(f"✅ Email tool handles list input: {len(parsed_result)} emails processed")
        
        # Test entity extraction with single input
        extraction_tool = EntityExtractionTool()
        single_email_text = """
        EMAIL SUBJECT: Netflix Subscription
        FROM: netflix@example.com
        CONTENT: Your Netflix subscription of ₹649 will be charged on Feb 15, 2024
        """
        
        extraction_result = extraction_tool._run(single_email_text)
        print("✅ Entity extraction tool works with single input")
        
        # Test validation with dict input
        validation_tool = SchemaValidationTool()
        test_entity = {
            "merchant": "Netflix",
            "amount": 649.0,
            "entity_type": "subscription", 
            "category": "entertainment",
            "confidence_score": 0.9
        }
        
        validation_result = validation_tool._run(test_entity)
        result_data = json.loads(validation_result)
        print(f"✅ Validation tool handles dict input: {result_data['valid']}")
        
        # Test classification with validation result structure
        classification_tool = ClassificationTool()
        validation_structure = {
            "validated_data": test_entity,
            "valid": True,
            "errors": []
        }
        
        classification_result = classification_tool._run(validation_structure)
        result_data = json.loads(classification_result)
        print(f"✅ Classification tool handles validation structure: {result_data['classified']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Updated tools test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Finance Email Summarizer - System Tests")
    print("=" * 50)
    
    tests = [
        test_config,
        test_models,
        test_tools,
        test_email_simulation,
        test_sample_processing,
        test_crewai_agents,
        test_crewai_tasks,
        test_crewai_crew_creation,
        test_updated_tools_context
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! System is ready.")
        print("\n🚀 Next steps:")
        print("1. Set up your .env file with API keys")
        print("2. Run: python run_server.py")
        print("3. Test OAuth flow at http://localhost:8000/auth/google")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 