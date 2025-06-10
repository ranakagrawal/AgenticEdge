"""
Authentication page for Google OAuth flow
"""

import streamlit as st
from urllib.parse import urlparse, parse_qs
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_auth_handler, get_api_client
from config import UI_MESSAGES, SESSION_KEYS

st.set_page_config(
    page_title="Authentication - Finance Email Processor",
    page_icon="🔐",
    layout="wide"
)

def main():
    """Main authentication page function."""
    
    auth_handler = get_auth_handler()
    api_client = get_api_client()
    
    st.title("🔐 Authentication")
    st.markdown("### Google OAuth for Gmail Access")
    
    # Check if already authenticated
    if auth_handler.is_authenticated():
        st.success("✅ You are already authenticated!")
        
        user_info = auth_handler.get_user_info_display()
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("#### 👤 User Information")
            st.write(f"**Email:** {user_info['email']}")
            st.write(f"**User ID:** {user_info['user_id']}")
            st.write(f"**Status:** {user_info['status']}")
            
            st.markdown("#### 🎯 Next Steps")
            st.info("You can now proceed to process your emails!")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("📧 Process Emails", type="primary"):
                    st.switch_page("pages/2_📧_Process_Emails.py")
            
            with col_b:
                if st.button("📋 View Results"):
                    st.switch_page("pages/3_📋_View_Results.py")
        
        with col2:
            st.markdown("#### ⚙️ Account Actions")
            
            if st.button("🚪 Logout", type="secondary"):
                auth_handler.logout()
                st.success("Logged out successfully!")
                st.rerun()
            
            st.markdown("---")
            
            with st.expander("🔧 Advanced"):
                st.markdown("**Delete Account Data**")
                st.warning("This will delete all your processed data from the system.")
                
                if st.button("🗑️ Delete My Data", type="secondary"):
                    user_id = auth_handler.get_user_id()
                    if user_id:
                        result = api_client.delete_user_data(user_id)
                        if result["success"]:
                            st.success("Data deleted successfully!")
                            auth_handler.logout()
                            st.rerun()
                        else:
                            st.error(f"Failed to delete data: {result['error']}")
    
    else:
        # Not authenticated - show login flow
        st.info("🔑 Please authenticate with Google to access your Gmail")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("#### 🚀 Getting Started")
            st.markdown("""
            To use the Finance Email Processor, you need to:
            
            1. **Authenticate** with your Google account
            2. **Grant permission** to access your Gmail
            3. **Start processing** financial emails
            
            **What we access:**
            - ✅ Read-only access to your Gmail
            - ✅ Extract financial information from emails
            - ❌ We do NOT store email content
            - ❌ We do NOT send emails on your behalf
            """)
            
            st.markdown("#### 🔐 Start Authentication")
            
            # Authentication flow
            if st.button("🔑 Authenticate with Google", type="primary", use_container_width=True):
                with st.spinner("Getting authorization URL..."):
                    result = auth_handler.start_oauth_flow()
                    
                    if result["success"]:
                        auth_url = result["authorization_url"]
                        st.session_state["auth_url"] = auth_url
                        st.rerun()
                    else:
                        st.error(f"Failed to get authorization URL: {result['error']}")
            
            # Show OAuth flow steps
            if "auth_url" in st.session_state:
                auth_url = st.session_state["auth_url"]
                
                st.markdown("---")
                st.markdown("### 🚀 Complete Authentication")
                
                st.markdown("""
                **Step 1:** Click the button below to open Google OAuth in a new tab:
                """)
                
                # Create a link that opens in new tab
                st.markdown(f"""
                <a href="{auth_url}" target="_blank" style="
                    display: inline-block;
                    padding: 0.5rem 1rem;
                    background-color: #ff4b4b;
                    color: white;
                    text-decoration: none;
                    border-radius: 0.25rem;
                    font-weight: bold;
                ">🔗 Open Google OAuth (New Tab)</a>
                """, unsafe_allow_html=True)
                
                st.markdown("**Step 2:** Complete Google authentication in the new tab")
                
                st.markdown("**Step 3:** After authentication, you'll see a JSON response like:")
                st.code('''
{
  "status": "success",
  "user_id": "user_your_email_gmail_com", 
  "email": "your.email@gmail.com",
  "total_messages": 36051,
  "message": "Authentication successful"
}
                ''')
                
                st.markdown("**Step 4:** Come back here and enter your details below:")
                
                st.info("📋 Copy the `user_id` and `email` from the JSON response above")
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    completed_user_id = st.text_input(
                        "User ID from JSON:",
                        placeholder="user_yashstudy02_gmail_com",
                        help="Copy the user_id value from the authentication response",
                        key="completed_user_id"
                    )
                
                with col_b:
                    completed_email = st.text_input(
                        "Email from JSON:",
                        placeholder="your.email@gmail.com", 
                        help="Copy the email value from the authentication response",
                        key="completed_email"
                    )
                
                if st.button("✅ Complete Setup", type="primary", disabled=not (completed_user_id and completed_email)):
                    # Set session state
                    st.session_state[SESSION_KEYS["authenticated"]] = True
                    st.session_state[SESSION_KEYS["user_id"]] = completed_user_id
                    st.session_state[SESSION_KEYS["user_email"]] = completed_email
                    
                    # Clear auth URL
                    if "auth_url" in st.session_state:
                        del st.session_state["auth_url"]
                    
                    st.success(f"🎉 Authentication completed for {completed_email}!")
                    st.balloons()
                    st.rerun()
                
                st.markdown("---")
                
                # Reset option
                if st.button("🔄 Start Over", type="secondary"):
                    if "auth_url" in st.session_state:
                        del st.session_state["auth_url"]
                    st.rerun()
        
        with col2:
            st.markdown("#### ℹ️ Information")
            
            # System status
            with st.expander("🌐 Backend Status"):
                health_result = api_client.health_check()
                if health_result["success"]:
                    st.success("✅ Backend is online")
                    st.json(health_result["data"])
                else:
                    st.error("❌ Backend is offline")
                    st.write(health_result["error"])
            
            # OAuth flow info
            with st.expander("🔍 OAuth Flow Details"):
                st.markdown("""
                **OAuth 2.0 Flow:**
                1. Get authorization URL
                2. User authorizes in browser
                3. Google returns authorization code
                4. Exchange code for access tokens
                5. Store user session
                
                **Scopes Requested:**
                - Gmail read-only access
                - User profile information
                """)
            
            # Troubleshooting
            with st.expander("🐛 Troubleshooting"):
                st.markdown("""
                **Common Issues:**
                
                - **"Backend Offline"**: Make sure FastAPI server is running on port 8000
                - **"Invalid Code"**: Code expires quickly, try getting a new one
                - **"Permission Denied"**: Check if Google OAuth credentials are configured
                
                **Need Help?**
                Check the API Testing page for detailed diagnostics.
                """)


if __name__ == "__main__":
    main() 