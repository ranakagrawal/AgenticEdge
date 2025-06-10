"""
Main Streamlit Application for Finance Email Processor
"""

import streamlit as st
from config import STREAMLIT_CONFIG
from utils import get_api_client, get_auth_handler

# Configure page
st.set_page_config(**STREAMLIT_CONFIG)

def main():
    """Main application function."""
    
    # Initialize services
    api_client = get_api_client()
    auth_handler = get_auth_handler()
    
    # Sidebar navigation
    with st.sidebar:
        st.title("🔧 Finance Email Processor")
        st.markdown("---")
        
        # Show authentication status
        user_info = auth_handler.get_user_info_display()
        st.subheader("👤 Authentication Status")
        
        if auth_handler.is_authenticated():
            st.success(user_info["status"])
            st.write(f"**Email:** {user_info['email']}")
            st.write(f"**User ID:** {user_info['user_id']}")
            
            if st.button("🚪 Logout", type="secondary"):
                auth_handler.logout()
                st.rerun()
        else:
            st.warning("Not authenticated")
        
        st.markdown("---")
        
        # System status
        st.subheader("🌐 System Status")
        health_result = api_client.health_check()
        
        if health_result["success"]:
            st.success("✅ Backend Online")
            health_data = health_result["data"]
            if "services" in health_data:
                services = health_data["services"]
                for service, status in services.items():
                    st.write(f"• {service}: {status}")
        else:
            st.error("❌ Backend Offline")
            st.write(health_result["error"])
        
        st.markdown("---")
        
        # Navigation info
        st.subheader("📋 Navigation")
        st.write("Use the pages in the sidebar to:")
        st.write("• 🔐 Authenticate with Google")
        st.write("• 📧 Process emails") 
        st.write("• 📋 View results")
        st.write("• 🧪 Test API endpoints")
    
    # Main content area
    st.title("📧 Finance Email Processor")
    st.markdown("### AI-powered financial email processing system")
    
    # Welcome message and instructions
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        **Welcome to the Finance Email Processor!** 
        
        This application helps you:
        - 🔐 **Authenticate** with your Google account
        - 📧 **Process** financial emails from Gmail
        - 📋 **View** extracted financial entities
        - 🧪 **Test** system components
        
        **Getting Started:**
        1. Go to the **🔐 Authentication** page to sign in
        2. Use **📧 Process Emails** to start processing
        3. Check **📋 View Results** to see extracted data
        4. Use **🧪 API Testing** for debugging
        """)
        
        # Quick actions
        st.markdown("### 🚀 Quick Actions")
        
        if not auth_handler.is_authenticated():
            st.info("👈 Go to the **🔐 Authentication** page to sign in with Google")
            
            # Quick setup for already authenticated users
            with st.expander("⚡ Quick Setup (Already Completed OAuth?)"):
                st.markdown("**If you've already completed OAuth via the backend and got a JSON response:**")
                st.code('''
Example JSON response:
{
  "user_id": "user_yashstudy02_gmail_com",
  "email": "yashstudy02@gmail.com"
}
                ''')
                
                col_q1, col_q2 = st.columns(2)
                with col_q1:
                    quick_user_id = st.text_input(
                        "User ID from JSON:", 
                        placeholder="user_yashstudy02_gmail_com", 
                        key="quick_user",
                        help="Copy the user_id from your authentication response"
                    )
                with col_q2:
                    quick_email = st.text_input(
                        "Email from JSON:", 
                        placeholder="yashstudy02@gmail.com", 
                        key="quick_email",
                        help="Copy the email from your authentication response"
                    )
                
                if st.button("⚡ Quick Setup", disabled=not (quick_user_id and quick_email)):
                    from config import SESSION_KEYS
                    st.session_state[SESSION_KEYS["authenticated"]] = True
                    st.session_state[SESSION_KEYS["user_id"]] = quick_user_id
                    st.session_state[SESSION_KEYS["user_email"]] = quick_email
                    st.success(f"🎉 Quick setup complete for {quick_email}!")
                    st.rerun()
        else:
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                if st.button("📧 Process Emails", type="primary"):
                    st.switch_page("pages/2_📧_Process_Emails.py")
            
            with col_b:
                if st.button("📋 View Results"):
                    st.switch_page("pages/3_📋_View_Results.py")
            
            with col_c:
                if st.button("🧪 Test API"):
                    st.switch_page("pages/4_🧪_API_Testing.py")
    
    with col2:
        st.markdown("### 🔧 System Info")
        
        # API endpoints info
        with st.expander("🌐 API Endpoints"):
            st.code(f"""
Backend URL: {api_client.base_url}

Available endpoints:
• GET  /health
• GET  /auth/google  
• GET  /auth/google/callback
• POST /process/emails/{{user_id}}
• GET  /process/status/{{run_id}}
• GET  /users/{{user_id}}/profile
• GET  /users/{{user_id}}/entities
            """)
        
        # Tech stack info
        with st.expander("💻 Tech Stack"):
            st.markdown("""
            **Backend:**
            - FastAPI + CrewAI
            - LangChain + OpenAI
            - Gmail API
            
            **Frontend:**
            - Streamlit
            - Pandas
            - Requests
            """)


if __name__ == "__main__":
    main() 