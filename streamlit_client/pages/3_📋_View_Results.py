"""
Results viewing page for displaying processed financial data
"""

import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_auth_handler, get_api_client

st.set_page_config(
    page_title="View Results - Finance Email Processor",
    page_icon="📋",
    layout="wide"
)

def main():
    """Main results viewing page function."""
    
    auth_handler = get_auth_handler()
    api_client = get_api_client()
    
    st.title("📋 View Results")
    st.markdown("### Extracted financial entities from your emails")
    
    # Check authentication
    if not auth_handler.require_auth():
        return
    
    user_id = auth_handler.get_user_id()
    user_email = auth_handler.get_user_email()
    
    # User info header
    st.info(f"👤 Viewing results for: **{user_email}** (ID: `{user_id}`)")
    
    # Filters and controls
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        entity_type_filter = st.selectbox(
            "🏷️ Entity Type",
            options=["All", "SUBSCRIPTION", "CREDIT_CARD", "BANK_STATEMENT", "INVESTMENT", "OTHER"],
            help="Filter by entity type"
        )
    
    with col2:
        category_filter = st.selectbox(
            "📂 Category",
            options=["All", "ENTERTAINMENT", "UTILITIES", "BANKING", "SHOPPING", "FOOD", "TRANSPORT", "OTHER"],
            help="Filter by category"
        )
    
    with col3:
        sort_by = st.selectbox(
            "🔄 Sort by",
            options=["Date (newest)", "Date (oldest)", "Amount (high)", "Amount (low)", "Merchant (A-Z)"],
            help="Sort results"
        )
    
    with col4:
        if st.button("🔄 Refresh", type="secondary"):
            st.rerun()
    
    # Get entities data
    entity_type_param = None if entity_type_filter == "All" else entity_type_filter.lower()
    category_param = None if category_filter == "All" else category_filter.lower()
    
    entities_result = api_client.get_user_entities(
        user_id=user_id,
        entity_type=entity_type_param,
        category=category_param
    )
    
    if not entities_result["success"]:
        st.error(f"❌ Failed to fetch entities: {entities_result['error']}")
        return
    
    entities_data = entities_result["data"]
    entities = entities_data.get("entities", [])
    
    if not entities:
        st.warning("📭 No financial entities found. Try processing some emails first!")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("📧 Process Emails", type="primary"):
                st.switch_page("pages/2_📧_Process_Emails.py")
        
        with col_b:
            if st.button("🧪 Test System"):
                st.switch_page("pages/4_🧪_API_Testing.py")
        
        return
    
    # Summary metrics
    st.markdown("### 📊 Summary")
    
    # Calculate metrics
    total_entities = len(entities)
    total_amount = sum(float(entity.get("amount", 0)) for entity in entities)
    unique_merchants = len(set(entity.get("merchant", "Unknown") for entity in entities))
    avg_confidence = sum(float(entity.get("confidence_score", 0)) for entity in entities) / total_entities if entities else 0
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.metric("🎯 Total Entities", total_entities)
    
    with col_m2:
        st.metric("💰 Total Amount", f"₹{total_amount:,.2f}")
    
    with col_m3:
        st.metric("🏪 Unique Merchants", unique_merchants)
    
    with col_m4:
        st.metric("🎲 Avg Confidence", f"{avg_confidence:.1%}")
    
    # Convert to DataFrame for better display
    df = pd.DataFrame(entities)
    
    # Sort data
    if sort_by == "Date (newest)":
        df = df.sort_values("due_date", ascending=False) if "due_date" in df.columns else df
    elif sort_by == "Date (oldest)":
        df = df.sort_values("due_date", ascending=True) if "due_date" in df.columns else df
    elif sort_by == "Amount (high)":
        df = df.sort_values("amount", ascending=False) if "amount" in df.columns else df
    elif sort_by == "Amount (low)":
        df = df.sort_values("amount", ascending=True) if "amount" in df.columns else df
    elif sort_by == "Merchant (A-Z)":
        df = df.sort_values("merchant", ascending=True) if "merchant" in df.columns else df
    
    # Data table
    st.markdown("### 📋 Entities Table")
    
    # Table configuration
    col_config = {
        "merchant": st.column_config.TextColumn("🏪 Merchant", width="medium"),
        "amount": st.column_config.NumberColumn("💰 Amount", format="₹%.2f", width="small"),
        "currency": st.column_config.TextColumn("💱 Currency", width="small"),
        "due_date": st.column_config.DateColumn("📅 Due Date", width="medium"),
        "entity_type": st.column_config.TextColumn("🏷️ Type", width="medium"),
        "category": st.column_config.TextColumn("📂 Category", width="medium"),
        "confidence_score": st.column_config.ProgressColumn("🎲 Confidence", min_value=0, max_value=1, width="small"),
        "email_source": st.column_config.TextColumn("📧 Email ID", width="large")
    }
    
    # Display editable dataframe
    if not df.empty:
        # Select columns to display
        display_columns = st.multiselect(
            "📋 Select columns to display:",
            options=list(df.columns),
            default=["merchant", "amount", "currency", "due_date", "entity_type", "category", "confidence_score"],
            help="Choose which columns to show in the table"
        )
        
        if display_columns:
            display_df = df[display_columns].copy()
            
            # Format dates if present
            if "due_date" in display_df.columns:
                display_df["due_date"] = pd.to_datetime(display_df["due_date"], errors="coerce")
            
            # Display data
            st.dataframe(
                display_df,
                column_config=col_config,
                use_container_width=True,
                hide_index=True
            )
            
            # Export options
            st.markdown("### 📤 Export Data")
            
            col_e1, col_e2, col_e3 = st.columns(3)
            
            with col_e1:
                csv_data = display_df.to_csv(index=False)
                st.download_button(
                    label="📄 Download CSV",
                    data=csv_data,
                    file_name=f"financial_entities_{user_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            
            with col_e2:
                json_data = display_df.to_json(orient="records", indent=2)
                st.download_button(
                    label="📋 Download JSON",
                    data=json_data,
                    file_name=f"financial_entities_{user_id}_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
            
            with col_e3:
                if st.button("🔍 View Raw Data"):
                    st.json(entities[:5])  # Show first 5 raw entities
        
        else:
            st.warning("Please select at least one column to display")
    
    # Detailed entity view
    st.markdown("### 🔍 Detailed View")
    
    if entities:
        entity_index = st.selectbox(
            "Select entity to view details:",
            options=range(len(entities)),
            format_func=lambda x: f"{entities[x].get('merchant', 'Unknown')} - ₹{entities[x].get('amount', 0)} ({entities[x].get('entity_type', 'Unknown')})"
        )
        
        selected_entity = entities[entity_index]
        
        col_d1, col_d2 = st.columns([2, 1])
        
        with col_d1:
            st.markdown("#### 📋 Entity Details")
            
            detail_data = {
                "🏪 Merchant": selected_entity.get("merchant", "N/A"),
                "💰 Amount": f"₹{selected_entity.get('amount', 0)}",
                "💱 Currency": selected_entity.get("currency", "N/A"),
                "📅 Due Date": selected_entity.get("due_date", "N/A"),
                "🏷️ Entity Type": selected_entity.get("entity_type", "N/A"),
                "📂 Category": selected_entity.get("category", "N/A"),
                "🎲 Confidence": f"{float(selected_entity.get('confidence_score', 0)):.1%}",
                "📧 Email Source": selected_entity.get("email_source", "N/A"),
                "👤 User ID": selected_entity.get("user_id", "N/A"),
                "🔗 Entity ID": selected_entity.get("id", "N/A")
            }
            
            for key, value in detail_data.items():
                st.write(f"**{key}:** {value}")
        
        with col_d2:
            st.markdown("#### 🔧 Entity Actions")
            
            if st.button("📄 View Full JSON"):
                st.json(selected_entity)
            
            if st.button("📋 Copy Entity ID"):
                entity_id = selected_entity.get("id", "No ID")
                st.code(entity_id)
                st.success("Entity ID displayed above!")
            
            # Entity confidence
            confidence = float(selected_entity.get("confidence_score", 0))
            if confidence >= 0.8:
                st.success(f"🎯 High confidence ({confidence:.1%})")
            elif confidence >= 0.6:
                st.warning(f"⚠️ Medium confidence ({confidence:.1%})")
            else:
                st.error(f"❌ Low confidence ({confidence:.1%})")


if __name__ == "__main__":
    main() 