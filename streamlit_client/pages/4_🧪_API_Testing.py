"""
API testing page for debugging and testing individual endpoints
"""

import streamlit as st
import json
import requests
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_auth_handler, get_api_client
from config import API_ENDPOINTS

st.set_page_config(
    page_title="API Testing - Finance Email Processor",
    page_icon="🧪",
    layout="wide"
)

def main():
    """Main API testing page function."""
    
    auth_handler = get_auth_handler()
    api_client = get_api_client()
    
    st.title("🧪 API Testing")
    st.markdown("### Debug and test individual API endpoints")
    
    # System status overview
    st.markdown("#### 🌐 System Status")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Health check
        if st.button("🔄 Check System Health", type="primary"):
            with st.spinner("Checking system health..."):
                health_result = api_client.health_check()
                
                if health_result["success"]:
                    st.success("✅ System is healthy!")
                    st.json(health_result["data"])
                else:
                    st.error("❌ System health check failed!")
                    st.error(health_result["error"])
    
    with col2:
        # Authentication status
        st.markdown("**Authentication Status:**")
        if auth_handler.is_authenticated():
            st.success("✅ Authenticated")
            st.write(f"User: {auth_handler.get_user_email()}")
        else:
            st.warning("⚠️ Not authenticated")
    
    # API endpoint testing
    st.markdown("---")
    st.markdown("#### 🔧 API Endpoint Testing")
    
    # Select endpoint to test
    endpoint_options = {
        "Health Check": ("GET", "/health", "Check system health"),
        "Get Auth URL": ("GET", "/auth/google", "Get Google OAuth URL"),
        "User Profile": ("GET", "/users/{user_id}/profile", "Get user profile"),
        "User Entities": ("GET", "/users/{user_id}/entities", "Get user entities"),
        "Process Emails": ("POST", "/process/emails/{user_id}", "Start email processing"),
        "Processing Status": ("GET", "/process/status/{run_id}", "Get processing status")
    }
    
    selected_endpoint = st.selectbox(
        "🎯 Select endpoint to test:",
        options=list(endpoint_options.keys()),
        help="Choose an API endpoint to test"
    )
    
    method, path, description = endpoint_options[selected_endpoint]
    
    st.info(f"**{method}** `{path}` - {description}")
    
    # Endpoint-specific testing
    if selected_endpoint == "Health Check":
        test_health_endpoint(api_client)
    
    elif selected_endpoint == "Get Auth URL":
        test_auth_url_endpoint(api_client)
    
    elif selected_endpoint == "User Profile":
        test_user_profile_endpoint(api_client, auth_handler)
    
    elif selected_endpoint == "User Entities":
        test_user_entities_endpoint(api_client, auth_handler)
    
    elif selected_endpoint == "Process Emails":
        test_process_emails_endpoint(api_client, auth_handler)
    
    elif selected_endpoint == "Processing Status":
        test_processing_status_endpoint(api_client)
    
    # Raw API testing
    st.markdown("---")
    st.markdown("#### 🔍 Raw API Testing")
    
    with st.expander("🛠️ Custom API Request"):
        st.markdown("**Make custom API requests for advanced testing**")
        
        col_raw1, col_raw2 = st.columns([1, 3])
        
        with col_raw1:
            custom_method = st.selectbox("Method:", ["GET", "POST", "PUT", "DELETE"])
            
        with col_raw2:
            custom_endpoint = st.text_input(
                "Endpoint path:",
                placeholder="/endpoint/path",
                help="Enter the API endpoint path"
            )
        
        custom_headers = st.text_area(
            "Headers (JSON):",
            value='{"Content-Type": "application/json"}',
            help="Enter headers as JSON"
        )
        
        custom_body = st.text_area(
            "Request body (JSON):",
            placeholder='{"key": "value"}',
            help="Enter request body as JSON (for POST/PUT requests)"
        )
        
        if st.button("🚀 Send Custom Request"):
            send_custom_request(custom_method, custom_endpoint, custom_headers, custom_body)
    
    # System diagnostics
    st.markdown("---")
    st.markdown("#### 🔍 System Diagnostics")
    
    col_diag1, col_diag2 = st.columns(2)
    
    with col_diag1:
        if st.button("📋 View All Endpoints"):
            st.markdown("**Available API Endpoints:**")
            for name, (method, path, desc) in endpoint_options.items():
                st.write(f"• **{method}** `{path}` - {desc}")
    
    with col_diag2:
        if st.button("⚙️ View Configuration"):
            st.markdown("**Current Configuration:**")
            st.json({
                "API_BASE_URL": api_client.base_url,
                "ENDPOINTS": API_ENDPOINTS,
                "SESSION_STATE": dict(st.session_state)
            })


def test_health_endpoint(api_client):
    """Test health endpoint."""
    st.markdown("##### 🏥 Health Check Test")
    
    if st.button("🔄 Test Health Endpoint"):
        with st.spinner("Testing health endpoint..."):
            result = api_client.health_check()
            display_api_result(result)


def test_auth_url_endpoint(api_client):
    """Test auth URL endpoint."""
    st.markdown("##### 🔐 Auth URL Test")
    
    if st.button("🔄 Test Auth URL Endpoint"):
        with st.spinner("Testing auth URL endpoint..."):
            result = api_client.get_auth_url()
            display_api_result(result)
            
            if result["success"] and "authorization_url" in result["data"]:
                st.markdown("**Authorization URL:**")
                st.code(result["data"]["authorization_url"])


def test_user_profile_endpoint(api_client, auth_handler):
    """Test user profile endpoint."""
    st.markdown("##### 👤 User Profile Test")
    
    if not auth_handler.is_authenticated():
        st.warning("Authentication required for this endpoint")
        return
    
    user_id = auth_handler.get_user_id()
    st.write(f"Testing for user: `{user_id}`")
    
    if st.button("🔄 Test User Profile Endpoint"):
        with st.spinner("Testing user profile endpoint..."):
            result = api_client.get_user_profile(user_id)
            display_api_result(result)


def test_user_entities_endpoint(api_client, auth_handler):
    """Test user entities endpoint."""
    st.markdown("##### 🎯 User Entities Test")
    
    if not auth_handler.is_authenticated():
        st.warning("Authentication required for this endpoint")
        return
    
    user_id = auth_handler.get_user_id()
    st.write(f"Testing for user: `{user_id}`")
    
    col1, col2 = st.columns(2)
    
    with col1:
        entity_type = st.selectbox(
            "Entity Type Filter:",
            ["None", "subscription", "credit_card", "bank_statement"],
            key="test_entity_type"
        )
    
    with col2:
        category = st.selectbox(
            "Category Filter:",
            ["None", "entertainment", "banking", "utilities"],
            key="test_category"
        )
    
    if st.button("🔄 Test User Entities Endpoint"):
        with st.spinner("Testing user entities endpoint..."):
            entity_type_param = None if entity_type == "None" else entity_type
            category_param = None if category == "None" else category
            
            result = api_client.get_user_entities(
                user_id, 
                entity_type=entity_type_param,
                category=category_param
            )
            display_api_result(result)


def test_process_emails_endpoint(api_client, auth_handler):
    """Test process emails endpoint."""
    st.markdown("##### 📧 Process Emails Test")
    
    if not auth_handler.is_authenticated():
        st.warning("Authentication required for this endpoint")
        return
    
    user_id = auth_handler.get_user_id()
    st.write(f"Testing for user: `{user_id}`")
    
    col1, col2 = st.columns(2)
    
    with col1:
        days_back = st.number_input(
            "Days back:",
            min_value=1,
            max_value=365,
            value=30,
            key="test_days_back"
        )
    
    with col2:
        max_emails = st.number_input(
            "Max emails:",
            min_value=1,
            max_value=1000,
            value=10,
            key="test_max_emails"
        )
    
    if st.button("🔄 Test Process Emails Endpoint"):
        st.warning("⚠️ This will actually start processing emails!")
        
        with st.spinner("Testing process emails endpoint..."):
            result = api_client.process_emails(
                user_id=user_id,
                days_back=days_back,
                max_emails=max_emails
            )
            display_api_result(result)


def test_processing_status_endpoint(api_client):
    """Test processing status endpoint."""
    st.markdown("##### 📊 Processing Status Test")
    
    run_id = st.text_input(
        "Run ID:",
        placeholder="Enter a processing run ID to check status",
        help="Get run ID from process emails response",
        key="test_run_id"
    )
    
    if st.button("🔄 Test Processing Status Endpoint", disabled=not run_id):
        with st.spinner("Testing processing status endpoint..."):
            result = api_client.get_processing_status(run_id)
            display_api_result(result)


def send_custom_request(method, endpoint, headers_str, body_str):
    """Send a custom API request."""
    try:
        # Parse headers
        headers = json.loads(headers_str) if headers_str else {}
        
        # Parse body
        body = json.loads(body_str) if body_str and method in ["POST", "PUT"] else None
        
        # Build URL
        base_url = API_ENDPOINTS["root"].rstrip("/")
        url = f"{base_url}{endpoint}"
        
        st.write(f"**Sending {method} request to:** `{url}`")
        
        # Make request
        with st.spinner("Sending request..."):
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=body, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=body, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            
            # Display response
            st.write(f"**Status Code:** {response.status_code}")
            
            try:
                response_json = response.json()
                st.write("**Response:**")
                st.json(response_json)
            except:
                st.write("**Response Text:**")
                st.code(response.text)
                
    except json.JSONDecodeError as e:
        st.error(f"JSON parsing error: {e}")
    except requests.exceptions.RequestException as e:
        st.error(f"Request error: {e}")
    except Exception as e:
        st.error(f"Error: {e}")


def display_api_result(result):
    """Display API result in a formatted way."""
    if result["success"]:
        st.success("✅ Request successful!")
        st.json(result["data"])
    else:
        st.error("❌ Request failed!")
        st.error(result["error"])


if __name__ == "__main__":
    main() 