"""
Authentication handler for managing OAuth flow and session state
"""

import streamlit as st
import sys
import os
from typing import Optional, Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SESSION_KEYS, UI_MESSAGES


class AuthHandler:
    """Handle authentication flow and session management."""
    
    def __init__(self):
        # Import here to avoid circular imports
        from .api_client import get_api_client
        self.api_client = get_api_client()
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state variables."""
        for key in SESSION_KEYS.values():
            if key not in st.session_state:
                st.session_state[key] = None
                
        # Initialize authentication status
        if SESSION_KEYS["authenticated"] not in st.session_state:
            st.session_state[SESSION_KEYS["authenticated"]] = False
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return bool(st.session_state.get(SESSION_KEYS["authenticated"], False))
    
    def get_user_id(self) -> Optional[str]:
        """Get current user ID."""
        return st.session_state.get(SESSION_KEYS["user_id"])
    
    def get_user_email(self) -> Optional[str]:
        """Get current user email."""
        return st.session_state.get(SESSION_KEYS["user_email"])
    
    def start_oauth_flow(self) -> Dict[str, Any]:
        """Start Google OAuth flow."""
        result = self.api_client.get_auth_url()
        
        if result["success"]:
            auth_data = result["data"]
            st.session_state[SESSION_KEYS["auth_code"]] = auth_data.get("state")
            return {
                "success": True,
                "authorization_url": auth_data["authorization_url"],
                "state": auth_data["state"]
            }
        else:
            return {"success": False, "error": result["error"]}
    
    def handle_oauth_callback(self, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """Handle OAuth callback and complete authentication."""
        result = self.api_client.handle_auth_callback(code, state)
        
        if result["success"]:
            auth_data = result["data"]
            
            # Store user information in session state
            st.session_state[SESSION_KEYS["authenticated"]] = True
            st.session_state[SESSION_KEYS["user_id"]] = auth_data.get("user_id")
            st.session_state[SESSION_KEYS["user_email"]] = auth_data.get("email")
            
            return {
                "success": True,
                "user_id": auth_data.get("user_id"),
                "email": auth_data.get("email"),
                "message": auth_data.get("message", UI_MESSAGES["auth_success"])
            }
        else:
            return {"success": False, "error": result["error"]}
    
    def logout(self):
        """Clear authentication and session data."""
        for key in SESSION_KEYS.values():
            if key in st.session_state:
                del st.session_state[key]
        
        # Reinitialize session state
        self._init_session_state()
    
    def require_auth(self) -> bool:
        """Check if authentication is required and show message if not authenticated."""
        if not self.is_authenticated():
            st.warning(UI_MESSAGES["auth_required"])
            st.info("👈 Please go to the Authentication page to sign in with Google")
            return False
        return True
    
    def get_user_info_display(self) -> Dict[str, str]:
        """Get user information for display purposes."""
        if not self.is_authenticated():
            return {"status": "Not authenticated"}
        
        return {
            "status": "Authenticated ✅",
            "user_id": self.get_user_id() or "Unknown",
            "email": self.get_user_email() or "Unknown"
        }


# Global auth handler instance
@st.cache_resource
def get_auth_handler() -> AuthHandler:
    """Get cached auth handler instance."""
    return AuthHandler() 