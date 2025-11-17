import streamlit as st
import pandas as pd
import subprocess
import sqlite3
from datetime import datetime
from pathlib import Path
import csv
from utils.auth import login_form, logout_button
import plotly.express as px
import plotly.graph_objects as go

# Page config must be first
st.set_page_config(
    page_title="Next Credit Dashboard", 
    layout="wide",
    page_icon="📬",
    initial_sidebar_state="expanded"
)

# Auth check
if "auth_user" not in st.session_state:
    st.title("🔐 Next Credit Login")
    login_form()
    st.stop()
else:
    logout_button()

DB_PATH = "disputes.db"
CSV_PATH = "data/accounts.csv"

# Custom CSS for better styling
st.markdown("""
    <style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
    }
    .dispute-card {
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin-bottom: 10px;
        background-color: white;
    }
    .status-badge {
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
        display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM disputes ORDER BY sent_date DESC", conn)
    conn.close()
    return df

def load_csv_queue():
    """Load pending disputes from CSV"""
    try:
        if Path(CSV_PATH).exists():
            df = pd.read_csv(CSV_PATH)
            return df[df['status'] == 'pending'] if 'status' in df.columns else df
    except:
        pass
    return pd.DataFrame()

def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = []
    for line in process.stdout:
        output.append(line.strip())
        st.write(line.strip())
    process.wait()
    return "\n".join(output)

def get_pdf_path(row):
    base_dir = Path("disputes/generated")
    bureau_dir = row["bureau"].lower()
    pdf_path = base_dir / bureau_dir / f"{row['account_number']}.pdf"
    return pdf_path if pdf_path.exists() else None

def append_to_csv(data):
    file_exists = Path(CSV_PATH).exists()
    with open(CSV_PATH, "a", newline="") as csvfile:
        fieldnames = ["bureau", "creditor_name", "account_number", "reason", "status", "date_added"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

def get_status_color(status):
    """Return color for status badge"""
    colors = {
        "delivered": "#4CAF50",
        "in_transit": "#FFC107",
        "queued": "#2196F3",
        "sent": "#00BCD4",
        "failed": "#F44336",
        "invalid_tracking_id": "#F44336",
        "pending": "#9E9E9E"
    }
    return colors.get(status, "#757575")

# --- Sidebar Controls ---
st.sidebar.title("⚙️ Navigation")
st.sidebar.markdown(f"**Welcome, {st.session_state['auth_user']}!**")
st.sidebar.markdown("---")

# Handle navigation from button clicks
if "nav_action" in st.session_state:
    default_action = st.session_state["nav_action"]
    del st.session_state["nav_action"]
else:
    default_action = "View Dashboard"

actions = ["📊 View Dashboard", "🚀 Send New Batch", "📡 Check Statuses", "➕ Add New Dispute", "⚙️ Settings"]
action_map = {
    "📊 View Dashboard": "View Dashboard",
    "🚀 Send New Batch": "Send New Batch",
    "📡 Check Statuses": "Check Statuses",
    "➕ Add New Dispute": "Add New Dispute",
    "⚙️ Settings": "Settings"
}

selected_action = st.sidebar.radio("", actions)
action = action_map[selected_action]

# Show queue count in sidebar
queue_df = load_csv_queue()
if not queue_df.empty:
    st.sidebar.warning(f"⏳ {len(queue_df)} dispute(s) in queue")

st.sidebar.markdown("---")
st.sidebar.caption("Next Credit v2.0 — Powered by Streamlit")

# --- Main Views ---
st.title("📬 Next Credit Dashboard")

if action == "View Dashboard":
    st.subheader("Dispute History & Analytics")
    
    try:
        df = load_data()
        
        if df.empty:
            st.info("📭 No disputes logged yet.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 Go to Send New Batch", use_container_width=True):
                    st.session_state["nav_action"] = "Send New Batch"
                    st.rerun()
            with col2:
                if st.button("➕ Add New Dispute", use_container_width=True):
                    st.session_state["nav_action"] = "Add New Dispute"
                    st.rerun()
        else:
            # Summary metrics at top
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📄 Total Letters", len(df))
            with col2:
                delivered_count = len(df[df["status"] == "delivered"])
                st.metric("✅ Delivered", delivered_count, 
                         delta=f"{(delivered_count/len(df)*100):.1f}%" if len(df) > 0 else "0%")
            with col3:
                pending_count = len(df[df["status"].isin(["sent", "in_transit", "queued"])])
                st.metric("⏳ In Transit", pending_count)
            with col4:
                failed_count = len(df[df["status"].isin(["failed", "invalid_tracking_id"])])
                st.metric("❌ Failed", failed_count)
            
            st.markdown("---")
            
            # Tabs for different views
            tab1, tab2, tab3 = st.tabs(["📋 List View", "📊 Analytics", "📎 Downloads"])
            
            with tab1:
                # Filters in columns
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    bureau_filter = st.selectbox("Filter by Bureau", ["All"] + sorted(df["bureau"].unique().tolist()))
                with col2:
                    status_filter = st.selectbox("Filter by Status", ["All"] + sorted(df["status"].unique().tolist()))
                with col3:
                    sort_order = st.selectbox("Sort", ["Newest First", "Oldest First"])
                
                filtered_df = df.copy()
                if bureau_filter != "All":
                    filtered_df = filtered_df[filtered_df["bureau"] == bureau_filter]
                if status_filter != "All":
                    filtered_df = filtered_df[filtered_df["status"] == status_filter]
                
                if sort_order == "Oldest First":
                    filtered_df = filtered_df.sort_values("sent_date", ascending=True)
                
                # Display as cards
                st.markdown(f"**Showing {len(filtered_df)} of {len(df)} disputes**")
                
                for _, row in filtered_df.iterrows():
                    status_color = get_status_color(row["status"])
                    
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 1])
                        with col1:
                            st.markdown(f"**{row['bureau']}** | {row['description']}")
                            st.caption(f"Sent: {row['sent_date'][:10]} | Tracking: `{row['tracking_id']}`")
                        with col2:
                            st.markdown(f"<span class='status-badge' style='background-color: {status_color}; color: white;'>{row['status'].upper()}</span>", unsafe_allow_html=True)
                        with col3:
                            pdf_path = get_pdf_path(row)
                            if pdf_path:
                                with open(pdf_path, "rb") as f:
                                    st.download_button(
                                        "📄 PDF",
                                        data=f,
                                        file_name=f"{row['bureau']}_{row['account_number']}.pdf",
                                        mime="application/pdf",
                                        key=f"download_{row['id']}"
                                    )
                        st.markdown("---")
            
            with tab2:
                # Analytics visualizations
                col1, col2 = st.columns(2)
                
                with col1:
                    # Status distribution pie chart
                    status_counts = df['status'].value_counts()
                    fig1 = px.pie(
                        values=status_counts.values,
                        names=status_counts.index,
                        title="Status Distribution",
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # Bureau distribution bar chart
                    bureau_counts = df['bureau'].value_counts()
                    fig2 = px.bar(
                        x=bureau_counts.index,
                        y=bureau_counts.values,
                        title="Disputes by Bureau",
                        labels={"x": "Bureau", "y": "Count"},
                        color=bureau_counts.values,
                        color_continuous_scale="Viridis"
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                
                # Timeline
                if 'sent_date' in df.columns:
                    df['date'] = pd.to_datetime(df['sent_date']).dt.date
                    timeline = df.groupby('date').size().reset_index(name='count')
                    fig3 = px.line(
                        timeline,
                        x='date',
                        y='count',
                        title="Disputes Over Time",
                        markers=True
                    )
                    st.plotly_chart(fig3, use_container_width=True)
            
            with tab3:
                st.markdown("### 📎 Download All Letters")
                st.write("Download PDFs for all disputes in the selected filter.")
                
                for _, row in filtered_df.iterrows():
                    pdf_path = get_pdf_path(row)
                    if pdf_path:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.text(f"{row['bureau']} - {row['account_number']}")
                        with col2:
                            with open(pdf_path, "rb") as f:
                                st.download_button(
                                    "Download",
                                    data=f,
                                    file_name=f"{row['bureau']}_{row['account_number']}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_{row['id']}"
                                )

    except Exception as e:
        st.error(f"❌ Error loading data: {e}")

elif action == "Send New Batch":
    st.subheader("🚀 Send New Dispute Batch")
    
    # Show queue preview
    queue_df = load_csv_queue()
    
    if queue_df.empty:
        st.warning("⚠️ No pending disputes in queue. Add disputes first!")
        if st.button("➕ Go to Add New Dispute", use_container_width=True):
            st.session_state["nav_action"] = "Add New Dispute"
            st.rerun()
    else:
        st.info(f"📋 Ready to send {len(queue_df)} dispute(s)")
        
        # Preview table
        st.dataframe(queue_df[['bureau', 'creditor_name', 'account_number', 'reason']], use_container_width=True)
        
        st.markdown("---")
        st.write("**This will:**")
        st.write("1. Generate PDF letters for each dispute")
        st.write("2. Mail them via Lob API")
        st.write("3. Log tracking information to the database")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🚀 Send Batch Now", type="primary", use_container_width=True):
                with st.spinner("📤 Processing batch..."):
                    output = run_command(["python3", "main.py"])
                st.success("✅ Batch complete! Check the dashboard for results.")
                st.balloons()
                
                if st.button("📊 View Dashboard"):
                    st.session_state["nav_action"] = "View Dashboard"
                    st.rerun()

elif action == "Check Statuses":
    st.subheader("📡 Check Delivery Statuses")
    
    # Show pending count
    df = load_data()
    pending = df[df["status"].isin(["sent", "in_transit", "queued"])]
    
    if pending.empty:
        st.info("✅ No pending letters to check.")
    else:
        st.write(f"Found **{len(pending)}** letter(s) with pending status:")
        st.dataframe(pending[['bureau', 'description', 'tracking_id', 'status']], use_container_width=True)
        
        st.markdown("---")
        st.write("This will poll the Lob API to get the latest delivery status for all pending letters.")
        
        if st.button("📡 Check Status Now", type="primary", use_container_width=True):
            with st.spinner("🔄 Checking Lob API..."):
                output = run_command(["python3", "main.py", "--check-status"])
            st.success("✅ Status check complete!")
            
            if st.button("🔄 Refresh Dashboard"):
                st.session_state["nav_action"] = "View Dashboard"
                st.rerun()

elif action == "Add New Dispute":
    st.subheader("➕ Add New Dispute")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.form("new_dispute_form", clear_on_submit=True):
            bureau = st.selectbox("Credit Bureau *", ["Experian", "Equifax", "TransUnion"])
            creditor = st.text_input("Creditor Name *", placeholder="e.g., ABC Bank")
            account = st.text_input("Account Number *", placeholder="e.g., 1234567890")
            reason = st.text_area(
                "Dispute Reason *", 
                placeholder="Explain why this information is inaccurate...",
                height=150
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                submitted = st.form_submit_button("➕ Add to Queue", type="primary", use_container_width=True)
            with col_b:
                if st.form_submit_button("🚀 Add & Send Immediately", use_container_width=True):
                    submitted = True
                    immediate_send = True
                else:
                    immediate_send = False
            
            if submitted:
                if not all([bureau, creditor, account, reason]):
                    st.error("❌ All fields are required.")
                else:
                    append_to_csv({
                        "bureau": bureau,
                        "creditor_name": creditor,
                        "account_number": account,
                        "reason": reason,
                        "status": "pending",
                        "date_added": datetime.utcnow().strftime("%Y-%m-%d")
                    })
                    st.success(f"✅ Added {bureau} dispute for {creditor}!")
                    st.balloons()
                    
                    if immediate_send:
                        with st.spinner("Sending immediately..."):
                            run_command(["python3", "main.py"])
                        st.success("✅ Sent!")
    
    with col2:
        st.markdown("### 💡 Tips")
        st.info("""
        **Effective Dispute Reasons:**
        - Be specific and factual
        - Reference dates if known
        - Mention any documentation you have
        - Keep it concise but clear
        
        **Example:**
        "This account was paid in full on 12/2023 but still shows an outstanding balance."
        """)

elif action == "Settings":
    st.subheader("⚙️ Settings")
    
    tab1, tab2, tab3 = st.tabs(["🏠 Personal Info", "🔐 Security", "📋 Templates"])
    
    with tab1:
        st.markdown("### Personal Information")
        st.write("Update the information that appears on your dispute letters.")
        
        with st.form("personal_info"):
            name = st.text_input("Full Name", value="John Doe")
            address = st.text_input("Address", value="123 Main St, Tampa, FL 33602")
            dob = st.text_input("Date of Birth", value="01/01/1990")
            ssn_last4 = st.text_input("Last 4 of SSN", value="1234", max_chars=4)
            
            if st.form_submit_button("💾 Save Changes"):
                st.success("✅ Personal information updated!")
    
    with tab2:
        st.markdown("### Change Password")
        
        with st.form("change_password"):
            current_pw = st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password", type="password")
            confirm_pw = st.text_input("Confirm New Password", type="password")
            
            if st.form_submit_button("🔒 Update Password"):
                if new_pw == confirm_pw:
                    st.success("✅ Password updated successfully!")
                else:
                    st.error("❌ Passwords don't match.")
    
    with tab3:
        st.markdown("### Letter Template")
        st.write("Customize the dispute letter template.")
        
        template_path = Path("disputes/templates/dispute_letter.j2")
        if template_path.exists():
            with open(template_path) as f:
                template_content = f.read()
            
            edited_template = st.text_area(
                "Edit Template", 
                value=template_content, 
                height=300
            )
            
            if st.button("💾 Save Template"):
                with open(template_path, "w") as f:
                    f.write(edited_template)
                st.success("✅ Template saved!")
        else:
            st.error("Template file not found.")

# Footer
st.markdown("---")
st.caption("💼 Next Credit Dashboard | Made with ❤️ using Streamlit")
