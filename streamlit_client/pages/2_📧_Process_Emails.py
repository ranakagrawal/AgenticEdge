"""
Email processing page for triggering and monitoring email processing
"""

import streamlit as st
import time
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_auth_handler, get_api_client
from config import SESSION_KEYS, UI_MESSAGES

st.set_page_config(
    page_title="Process Emails - Finance Email Processor",
    page_icon="📧",
    layout="wide"
)

def main():
    """Main email processing page function."""
    
    auth_handler = get_auth_handler()
    api_client = get_api_client()
    
    st.title("📧 Process Emails")
    st.markdown("### Extract financial information from your Gmail")
    
    # Check authentication
    if not auth_handler.require_auth():
        return
    
    user_id = auth_handler.get_user_id()
    user_email = auth_handler.get_user_email()
    
    # User info header
    st.info(f"👤 Processing emails for: **{user_email}** (ID: `{user_id}`)")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### ⚙️ Processing Configuration")
        
        # Processing parameters
        with st.form("processing_config"):
            st.markdown("**Email Range Settings:**")
            
            days_back = st.slider(
                "📅 Days to look back",
                min_value=7,
                max_value=365,
                value=180,
                help="How many days back to search for emails"
            )
            
            max_emails = st.slider(
                "📮 Maximum emails to process",
                min_value=10,
                max_value=1000,
                value=100,
                help="Limit the number of emails to process"
            )
            
            st.markdown("**Processing Options:**")
            
            col_a, col_b = st.columns(2)
            with col_a:
                process_new_only = st.checkbox(
                    "🆕 Process new emails only",
                    value=True,
                    help="Skip already processed emails"
                )
            
            with col_b:
                include_sent = st.checkbox(
                    "📤 Include sent emails",
                    value=False,
                    help="Also process emails from sent folder"
                )
            
            # Submit button
            submitted = st.form_submit_button(
                "🚀 Start Processing",
                type="primary",
                use_container_width=True
            )
            
            if submitted:
                # Start processing
                with st.spinner("🔄 Starting email processing..."):
                    try:
                        result = api_client.process_emails(
                            user_id=user_id,
                            days_back=days_back,
                            max_emails=max_emails
                        )
                        
                        if result["success"]:
                            processing_data = result["data"]
                            run_id = processing_data["run_id"]
                            
                            # Store run ID in session state
                            st.session_state[SESSION_KEYS["processing_run_id"]] = run_id
                            
                            st.success(f"✅ Processing completed! Run ID: `{run_id}`")
                            st.success(f"📊 Processed {processing_data.get('emails_processed', 'N/A')} emails")
                            st.success(f"🎯 Extracted {processing_data.get('entities_extracted', 'N/A')} entities")
                            
                            # Auto-refresh to show status
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to start processing: {result['error']}")
                    
                    except Exception as e:
                        st.error(f"❌ Processing error: {str(e)}")
                        st.info("💡 If processing is taking too long, check the backend logs or try with fewer emails.")
        
        # Processing status section
        st.markdown("---")
        st.markdown("#### 📊 Processing Status")
        
        current_run_id = st.session_state.get(SESSION_KEYS["processing_run_id"])
        
        # Option to manually enter run ID
        col_manual1, col_manual2 = st.columns([3, 1])
        with col_manual1:
            manual_run_id = st.text_input(
                "🔍 Or enter a Run ID to check status:",
                placeholder="run_20250610_215951_user_yas",
                help="Enter a run ID from a previous processing session"
            )
        with col_manual2:
            if st.button("📊 Check Status", disabled=not manual_run_id):
                st.session_state[SESSION_KEYS["processing_run_id"]] = manual_run_id
                st.rerun()
        
        if current_run_id:
            # Status monitoring
            col_status1, col_status2 = st.columns([3, 1])
            
            with col_status1:
                status_placeholder = st.empty()
                progress_placeholder = st.empty()
                
            with col_status2:
                if st.button("🔄 Refresh Status"):
                    st.rerun()
                
                if st.button("🛑 Clear Status"):
                    if SESSION_KEYS["processing_run_id"] in st.session_state:
                        del st.session_state[SESSION_KEYS["processing_run_id"]]
                    st.rerun()
            
            # Get and display status
            status_result = api_client.get_processing_status(current_run_id)
            
            if status_result["success"]:
                status_data = status_result["data"]
                
                with status_placeholder.container():
                    st.markdown(f"**Run ID:** `{current_run_id}`")
                    
                    status = status_data.get("status", "unknown")
                    
                    if status == "processing":
                        st.info(f"🔄 Status: {status.title()}")
                    elif status == "completed":
                        st.success(f"✅ Status: {status.title()}")
                    elif status == "failed":
                        st.error(f"❌ Status: {status.title()}")
                    else:
                        st.warning(f"⚠️ Status: {status.title()}")
                    
                    # Display metrics if available
                    if "emails_processed" in status_data:
                        col_m1, col_m2, col_m3 = st.columns(3)
                        
                        with col_m1:
                            st.metric(
                                "📧 Emails Processed",
                                status_data.get("emails_processed", 0)
                            )
                        
                        with col_m2:
                            st.metric(
                                "🎯 Entities Extracted",
                                status_data.get("entities_extracted", 0)
                            )
                        
                        with col_m3:
                            st.metric(
                                "⏱️ Processing Time",
                                f"{status_data.get('processing_time_seconds', 0):.1f}s"
                            )
                    
                    # Progress bar
                    if "progress_percentage" in status_data:
                        progress = status_data["progress_percentage"] / 100
                        with progress_placeholder:
                            st.progress(progress, text=f"Progress: {status_data['progress_percentage']:.1f}%")
                    
                    # Show detailed results if completed
                    if status == "completed" and "results" in status_data:
                        with st.expander("📋 Detailed Results"):
                            st.json(status_data["results"])
            else:
                with status_placeholder:
                    st.error(f"❌ Failed to get status: {status_result['error']}")
        
        else:
            st.info("ℹ️ No active processing session. Start processing above to monitor progress.")
    
    with col2:
        st.markdown("#### 📊 Quick Stats")
        
        # Get user profile for stats
        profile_result = api_client.get_user_profile(user_id)
        
        if profile_result["success"]:
            profile_data = profile_result["data"]
            
            st.metric(
                "📧 Total Emails",
                profile_data.get("total_emails_processed", 0)
            )
            
            st.metric(
                "🎯 Entities Found",
                profile_data.get("total_entities", 0)
            )
            
            last_sync = profile_data.get("last_sync")
            if last_sync:
                st.write(f"**Last Sync:** {last_sync}")
        
        st.markdown("---")
        
        # Processing tips
        with st.expander("💡 Processing Tips"):
            st.markdown("""
            **Optimize Processing:**
            - Start with fewer days (30-60) for testing
            - Increase max emails gradually
            - Monitor processing time
            
            **What Gets Processed:**
            - Bank statements
            - Credit card bills
            - Subscription payments
            - Purchase receipts
            - Investment updates
            """)
        
        # Recent activity
        with st.expander("📈 Recent Activity"):
            # Get recent entities
            entities_result = api_client.get_user_entities(user_id)
            
            if entities_result["success"]:
                entities = entities_result["data"].get("entities", [])
                
                if entities:
                    st.write(f"**Last {min(5, len(entities))} entities:**")
                    for entity in entities[:5]:
                        merchant = entity.get("merchant", "Unknown")
                        amount = entity.get("amount", 0)
                        currency = entity.get("currency", "INR")
                        st.write(f"• {merchant}: {currency} {amount}")
                else:
                    st.info("No entities found yet")
            else:
                st.warning("Could not fetch recent activity")
        
        # Auto-refresh option
        with st.expander("🔄 Auto-Refresh"):
            auto_refresh = st.checkbox(
                "Enable auto-refresh",
                help="Automatically refresh status every 5 seconds"
            )
            
            if auto_refresh and current_run_id:
                time.sleep(5)
                st.rerun()


if __name__ == "__main__":
    main() 