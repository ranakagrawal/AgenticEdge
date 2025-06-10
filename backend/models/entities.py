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
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True 