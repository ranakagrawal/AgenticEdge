"""Configuration settings for the Finance Email Summarizer."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """Application settings."""
    
    # API Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Google OAuth Configuration
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    
    # Database Configuration
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name: str = os.getenv("DATABASE_NAME", "finance_email_summarizer")
    
    # Application Configuration
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Gmail API Scopes (including openid to match Google's automatic addition)
    gmail_scopes: list[str] = [
        'openid',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ]
    
    # CrewAI Configuration
    crewai_verbose: bool = bool(os.getenv("CREWAI_VERBOSE", "true").lower() == "true")
    crewai_memory: bool = bool(os.getenv("CREWAI_MEMORY", "true").lower() == "true")
    crewai_max_execution_time: int = int(os.getenv("CREWAI_MAX_EXECUTION_TIME", "3600"))  # 1 hour
    crewai_max_iter: int = int(os.getenv("CREWAI_MAX_ITER", "3"))
    crewai_temperature: float = float(os.getenv("CREWAI_TEMPERATURE", "0.1"))
    
    # Task Configuration
    task_timeout_seconds: int = int(os.getenv("TASK_TIMEOUT_SECONDS", "300"))  # 5 minutes per task
    task_retry_attempts: int = int(os.getenv("TASK_RETRY_ATTEMPTS", "2"))
    
    # Processing Configuration
    email_batch_size: int = int(os.getenv("EMAIL_BATCH_SIZE", "50"))
    max_emails_per_run: int = int(os.getenv("MAX_EMAILS_PER_RUN", "100"))
    days_back_default: int = int(os.getenv("DAYS_BACK_DEFAULT", "180"))
    
    # LLM Configuration
    llm_model: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    llm_request_timeout: int = int(os.getenv("LLM_REQUEST_TIMEOUT", "30"))
    
    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings() 