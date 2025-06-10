"""Main FastAPI application for Finance Email Summarizer."""

import json
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from backend.config import settings
from backend.services.gmail_service import GmailService
from backend.services.email_processor import EmailProcessingService
from backend.models.entities import UserProfile, UserPreferences


# Pydantic models for requests/responses
class AuthResponse(BaseModel):
    authorization_url: str
    state: str


class ProcessEmailsRequest(BaseModel):
    days_back: int = 180
    max_emails: int = 100


class ProcessingResponse(BaseModel):
    run_id: str
    status: str
    message: str
    entities_extracted: int
    processing_url: str


# Initialize FastAPI app
app = FastAPI(
    title="Finance Email Summarizer API",
    description="AI-powered financial email processing system for Indian users",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
gmail_service = GmailService()
email_processor = EmailProcessingService()

# In-memory storage for demo (use Redis/Database in production)
user_sessions = {}
user_profiles = {}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Finance Email Summarizer API",
        "version": "1.0.0",
        "description": "AI-powered financial email processing system",
        "endpoints": {
            "auth": "/auth/google",
            "callback": "/auth/google/callback",
            "process": "/process/emails",
            "status": "/process/status/{run_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "gmail_service": "operational",
            "email_processor": "operational"
        }
    }


@app.get("/auth/google", response_model=AuthResponse)
async def initiate_google_auth():
    """Initiate Google OAuth flow for Gmail access."""
    
    try:
        # Get authorization URL from Gmail service
        auth_url = gmail_service.get_authorization_url()
        
        # Generate session state
        state = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Initiated Google OAuth flow with state: {state}")
        
        return AuthResponse(
            authorization_url=auth_url,
            state=state
        )
        
    except Exception as e:
        logger.error(f"Error initiating Google auth: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate authentication: {str(e)}")


@app.get("/auth/google/callback")
async def handle_google_callback(code: str = Query(...), state: str = Query(None)):
    """Handle Google OAuth callback and complete authentication."""
    
    try:
        # Exchange authorization code for tokens
        tokens = gmail_service.exchange_code_for_tokens(code)
        
        # Get user information
        user_info = gmail_service.get_user_info(
            tokens['access_token'], 
            tokens['refresh_token']
        )
        
        # Create user profile
        user_id = f"user_{user_info['email'].replace('@', '_').replace('.', '_')}"
        
        user_profile = UserProfile(
            user_id=user_id,
            email=user_info['email'],
            name=user_info['email'].split('@')[0],  # Use email prefix as name
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            last_sync=datetime.utcnow(),
            preferences=UserPreferences()
        )
        
        # Store user profile (in production, save to database)
        user_profiles[user_id] = user_profile
        user_sessions[state] = user_id
        
        logger.info(f"Successfully authenticated user: {user_profile.email}")
        
        # Return success page or redirect to frontend
        return JSONResponse(
            content={
                "status": "success",
                "message": "Authentication successful",
                "user_id": user_id,
                "email": user_profile.email,
                "total_messages": user_info.get('total_messages', 0),
                "next_step": "Call /process/emails to start processing financial emails"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in Google OAuth callback: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@app.post("/process/emails/{user_id}", response_model=ProcessingResponse)
async def process_user_emails(
    user_id: str,
    request: ProcessEmailsRequest = ProcessEmailsRequest()
):
    """Process financial emails for an authenticated user."""
    
    try:
        # Check if user exists
        if user_id not in user_profiles:
            raise HTTPException(status_code=404, detail="User not found. Please authenticate first.")
        
        user_profile = user_profiles[user_id]
        
        logger.info(f"Starting email processing for user: {user_profile.email}")
        
        # Process emails through the complete pipeline
        processing_result = await email_processor.process_user_emails(
            user_profile=user_profile,
            days_back=request.days_back,
            max_emails=request.max_emails
        )
        
        return ProcessingResponse(
            run_id=processing_result['run_id'],
            status=processing_result['status'],
            message=f"Successfully processed {processing_result['emails_processed']} emails",
            entities_extracted=processing_result['entities_extracted'],
            processing_url=f"/process/status/{processing_result['run_id']}"
        )
        
    except Exception as e:
        logger.error(f"Error processing emails for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process emails: {str(e)}")


@app.get("/process/status/{run_id}")
async def get_processing_status(run_id: str):
    """Get detailed processing status and results for a run."""
    
    try:
        # In production, this would query the database
        # For now, try to read from log file
        
        log_filename = f"logs/processing_{run_id}.json"
        
        try:
            with open(log_filename, 'r') as f:
                processing_data = json.load(f)
                
            return {
                "run_id": run_id,
                "status": "completed",
                "timestamp": processing_data.get('timestamp'),
                "entities_processed": processing_data.get('entities_processed', 0),
                "summary": processing_data.get('summary', {}),
                "entities": processing_data.get('entities', [])
            }
            
        except FileNotFoundError:
            return {
                "run_id": run_id,
                "status": "not_found",
                "message": "Processing run not found or still in progress"
            }
        
    except Exception as e:
        logger.error(f"Error getting processing status for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing status: {str(e)}")


@app.get("/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    """Get user profile information."""
    
    if user_id not in user_profiles:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_profile = user_profiles[user_id]
    
    # Return profile without sensitive tokens
    return {
        "user_id": user_profile.user_id,
        "email": user_profile.email,
        "name": user_profile.name,
        "last_sync": user_profile.last_sync.isoformat() if user_profile.last_sync else None,
        "preferences": user_profile.preferences.dict(),
        "created_at": user_profile.created_at.isoformat()
    }


@app.get("/users/{user_id}/entities")
async def get_user_entities(
    user_id: str,
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """Get financial entities for a user with optional filtering."""
    
    if user_id not in user_profiles:
        raise HTTPException(status_code=404, detail="User not found")
    
    # In production, this would query the database
    # For now, return a placeholder response
    
    return {
        "user_id": user_id,
        "entities": [],
        "filters": {
            "entity_type": entity_type,
            "category": category
        },
        "summary": {
            "total_entities": 0,
            "total_amount": 0,
            "by_type": {
                "subscriptions": 0,
                "bills": 0,
                "loans": 0
            }
        },
        "message": "Entity storage not implemented yet. Check processing logs for extracted entities."
    }


@app.delete("/users/{user_id}")
async def delete_user_data(user_id: str):
    """Delete all user data (for privacy compliance)."""
    
    if user_id not in user_profiles:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Remove user from in-memory storage
    del user_profiles[user_id]
    
    # Remove user from sessions
    for state, uid in list(user_sessions.items()):
        if uid == user_id:
            del user_sessions[state]
    
    logger.info(f"Deleted all data for user: {user_id}")
    
    return {
        "status": "success",
        "message": "User data deleted successfully",
        "user_id": user_id
    }


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with proper logging."""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logger.add("logs/app.log", rotation="1 day", retention="30 days")
    
    # Run the application
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 