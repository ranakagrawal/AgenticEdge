"""Data models for finance entities."""

from datetime import datetime
from typing import Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated


# Custom ObjectId validation for MongoDB
PyObjectId = Annotated[str, BeforeValidator(str)]


class EntityType(str, Enum):
    """Types of financial entities."""
    SUBSCRIPTION = "subscription"
    BILL = "bill"
    LOAN = "loan"


class EntityCategory(str, Enum):
    """Categories for financial entities."""
    # Subscription categories
    ENTERTAINMENT = "entertainment"
    PRODUCTIVITY = "productivity"
    CLOUD_STORAGE = "cloud_storage"
    
    # Bill categories
    UTILITY = "utility"
    CREDIT_CARD = "credit_card"
    MUNICIPAL = "municipal"
    MEDICAL = "medical"
    MISCELLANEOUS = "miscellaneous"
    
    # Loan categories
    HOME_LOAN = "home_loan"
    PERSONAL_LOAN = "personal_loan"
    EDUCATION_LOAN = "education_loan"
    VEHICLE_LOAN = "vehicle_loan"
    BNPL = "bnpl"


class EntityStatus(str, Enum):
    """Status of financial entities."""
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"


class PaymentEntity(BaseModel):
    """Core payment entity model."""
    
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    email_source: str = Field(..., description="Message ID from Gmail")
    merchant: str = Field(..., description="Service provider or merchant name")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="INR", description="Currency code")
    due_date: datetime = Field(..., description="Payment due date")
    entity_type: EntityType = Field(..., description="Type of entity")
    category: EntityCategory = Field(..., description="Category of the entity")
    auto_debit: bool = Field(default=False, description="Auto-debit enabled")
    status: EntityStatus = Field(default=EntityStatus.PENDING, description="Payment status")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")
    
    # Additional fields for different entity types
    billing_cycle: Optional[str] = Field(None, description="Billing cycle for subscriptions")
    principal_amount: Optional[float] = Field(None, description="Principal amount for loans")
    interest_amount: Optional[float] = Field(None, description="Interest amount for loans")
    late_fee: Optional[float] = Field(None, description="Late fee amount if any")
    
    # User association
    user_id: str = Field(..., description="User ID from Google OAuth")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "email_source": "msg_12345",
                "merchant": "Netflix",
                "amount": 649.00,
                "currency": "INR",
                "due_date": "2024-02-15T00:00:00Z",
                "entity_type": "subscription",
                "category": "entertainment",
                "auto_debit": True,
                "status": "pending",
                "confidence_score": 0.95,
                "user_id": "google_oauth_user_id"
            }
        }


class UserPreferences(BaseModel):
    """User preferences for notifications and processing."""
    
    notification_channels: list[Literal["email", "sms"]] = Field(default=["email"])
    reminder_days: int = Field(default=2, ge=1, le=30)
    scan_period_months: int = Field(default=6, ge=1, le=12)


class UserProfile(BaseModel):
    """User profile model."""
    
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str = Field(..., description="Google OAuth user ID")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User full name")
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    last_sync: Optional[datetime] = Field(None, description="Last email sync timestamp")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Gmail API tokens (encrypted)
    access_token: Optional[str] = Field(None, description="Encrypted access token")
    refresh_token: Optional[str] = Field(None, description="Encrypted refresh token")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class ProcessingRun(BaseModel):
    """Model to track processing runs."""
    
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    run_id: str = Field(..., description="Unique run identifier")
    user_id: str = Field(..., description="User ID")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    status: Literal["running", "completed", "failed"] = Field(default="running")
    emails_processed: int = Field(default=0)
    entities_extracted: int = Field(default=0)
    errors: list[str] = Field(default_factory=list)
    error_category: Optional[str] = Field(None, description="Error category for recovery")
    recovery_suggestions: list[str] = Field(default_factory=list, description="Recovery suggestions")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


# CrewAI Task Input/Output Models

class EmailData(BaseModel):
    """Model for email data structure."""
    
    message_id: str = Field(..., description="Gmail message ID")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")
    sender: str = Field(..., description="Sender email address", alias="from")
    date: datetime = Field(..., description="Email date")
    
    class Config:
        populate_by_name = True


class TaskContext(BaseModel):
    """Base model for task context data."""
    
    emails: list[EmailData] = Field(..., description="List of emails to process")
    user_profile: dict = Field(..., description="User profile information")
    run_id: str = Field(..., description="Processing run ID")
    user_id: str = Field(..., description="User ID")
    processing_params: dict = Field(default_factory=dict, description="Processing parameters")


class PreprocessedEmailData(BaseModel):
    """Model for preprocessed email data."""
    
    message_id: str = Field(..., description="Original message ID")
    clean_text: str = Field(..., description="Cleaned email text")
    extraction_ready: bool = Field(default=True, description="Ready for entity extraction")


class ExtractedEntityData(BaseModel):
    """Model for extracted entity data."""
    
    merchant: str = Field(..., description="Merchant name")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(default="INR", description="Currency")
    due_date: Optional[str] = Field(None, description="Due date in YYYY-MM-DD format")
    entity_type: str = Field(..., description="Entity type")
    category: str = Field(..., description="Entity category")
    auto_debit: Optional[bool] = Field(None, description="Auto debit status")
    billing_cycle: Optional[str] = Field(None, description="Billing cycle")
    principal_amount: Optional[float] = Field(None, description="Principal amount")
    interest_amount: Optional[float] = Field(None, description="Interest amount")
    late_fee: Optional[float] = Field(None, description="Late fee")
    confidence_score: float = Field(..., description="Extraction confidence")
    source_message_id: str = Field(..., description="Source email message ID")


class ValidationResult(BaseModel):
    """Model for validation results."""
    
    valid: bool = Field(..., description="Whether validation passed")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    validated_data: Optional[dict] = Field(None, description="Validated entity data")


class ClassificationResult(BaseModel):
    """Model for classification results."""
    
    classified: bool = Field(..., description="Whether classification succeeded")
    entity_data: dict = Field(..., description="Classified entity data")
    processing_rules: dict = Field(default_factory=dict, description="Processing rules")
    urgency_level: Optional[str] = Field(None, description="Urgency level")
    priority_score: Optional[int] = Field(None, description="Priority score")


class DeduplicationResult(BaseModel):
    """Model for deduplication results."""
    
    unique_entities: list[dict] = Field(..., description="Unique entities after deduplication")
    duplicate_info: list[dict] = Field(default_factory=list, description="Information about duplicates found")
    total_unique: int = Field(..., description="Total number of unique entities")
    duplicates_found: int = Field(default=0, description="Number of duplicates found")


class StorageResult(BaseModel):
    """Model for storage operation results."""
    
    stored_entities: list[dict] = Field(..., description="Successfully stored entities")
    total_stored: int = Field(..., description="Total number of entities stored")
    storage_errors: list[str] = Field(default_factory=list, description="Storage errors if any")


class ProcessingNotification(BaseModel):
    """Model for processing completion notifications."""
    
    run_id: str = Field(..., description="Processing run ID")
    user_id: str = Field(..., description="User ID")
    total_emails: int = Field(..., description="Total emails processed")
    entities_stored: int = Field(..., description="Entities successfully stored")
    processing_duration: float = Field(..., description="Processing time in seconds")
    urgent_payments: list[dict] = Field(default_factory=list, description="Urgent payments identified")
    errors: list[str] = Field(default_factory=list, description="Processing errors")
    recommendations: list[str] = Field(default_factory=list, description="User recommendations") 