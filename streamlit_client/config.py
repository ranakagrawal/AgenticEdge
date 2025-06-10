"""
Configuration for Streamlit Client
"""

import os
from typing import Dict, Any

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Streamlit Configuration
STREAMLIT_CONFIG: Dict[str, Any] = {
    "page_title": "Finance Email Processor",
    "page_icon": "📧",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# API Endpoints
API_ENDPOINTS = {
    "root": f"{API_BASE_URL}/",
    "health": f"{API_BASE_URL}/health",
    "auth_google": f"{API_BASE_URL}/auth/google",
    "auth_callback": f"{API_BASE_URL}/auth/google/callback",
    "process_emails": f"{API_BASE_URL}/process/emails",
    "process_status": f"{API_BASE_URL}/process/status",
    "user_profile": f"{API_BASE_URL}/users",
    "user_entities": f"{API_BASE_URL}/users"
}

# Session State Keys
SESSION_KEYS = {
    "authenticated": "authenticated",
    "user_id": "user_id",
    "user_email": "user_email", 
    "auth_code": "auth_code",
    "processing_run_id": "processing_run_id"
}

# UI Messages
UI_MESSAGES = {
    "auth_required": "🔐 Please authenticate with Google first",
    "auth_success": "✅ Authentication successful!",
    "processing_started": "🔄 Email processing started...",
    "processing_complete": "✅ Email processing completed!",
    "api_error": "❌ API Error occurred",
    "connection_error": "🌐 Connection error - check if backend is running"
} 