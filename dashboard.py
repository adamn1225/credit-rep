import streamlit as st
import pandas as pd
import subprocess
import sqlite3
from datetime import datetime
from pathlib import Path
import csv
from utils.auth import login_form, logout_button

if "auth_user" not in st.session_state:
    st.title("🔐 Credit Disputer Login")
    login_form()
    st.stop()
else:
    logout_button()

DB_PATH = "disputes.db"
CSV_PATH = "data/accounts.csv"

st.set_page_config(page_title="Credit Disputer Dashboard", layout="wide")

# --- Helper Functions ---
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM disputes ORDER BY sent_date DESC", conn)
    conn.close()
    return df

def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in process.stdout:
        st.write(line.strip())
    process.wait()

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

# --- Sidebar Controls ---
st.sidebar.title("⚙️ Controls")
action = st.sidebar.selectbox(
    "Choose an action",
    ["View Dashboard", "Send New Batch", "Check Statuses", "Add New Dispute"]
)
st.sidebar.markdown("---")
st.sidebar.caption("Credit Disputer UI — powered by Streamlit")

# --- Main Views ---
st.title("📬 Credit Disputer Dashboard")

if action == "View Dashboard":
    st.subheader("Dispute History")
    try:
        df = load_data()
        if df.empty:
            st.info("No disputes logged yet. Run a batch first.")
        else:
            # Filters
            bureau_filter = st.selectbox("Filter by Bureau", ["All"] + sorted(df["bureau"].unique().tolist()))
            status_filter = st.selectbox("Filter by Status", ["All"] + sorted(df["status"].unique().tolist()))

            filtered_df = df.copy()
            if bureau_filter != "All":
                filtered_df = filtered_df[filtered_df["bureau"] == bureau_filter]
            if status_filter != "All":
                filtered_df = filtered_df[filtered_df["status"] == status_filter]

            # Color-code rows
            def row_color(row):
                if row["status"] == "delivered":
                    return "background-color: #d1f7c4;"  # greenish
                elif row["status"] in ["failed", "invalid_tracking_id"]:
                    return "background-color: #f7c4c4;"  # red
                elif row["status"] in ["in_transit", "queued"]:
                    return "background-color: #f7f3c4;"  # yellow
                return ""

            styled_df = filtered_df.style.apply(lambda x: [row_color(x)], axis=1)
            st.dataframe(styled_df, use_container_width=True)

            # Summary metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("📄 Total Letters", len(df))
            col2.metric("✅ Delivered", len(df[df["status"] == "delivered"]))
            col3.metric("❌ Failed", len(df[df["status"] == "failed"]))

            # PDF View/Download
            st.markdown("### 📎 Download Letters")
            for _, row in filtered_df.iterrows():
                pdf_path = get_pdf_path(row)
                if pdf_path:
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label=f"Download {row['bureau']} Letter ({row['account_number']})",
                            data=f,
                            file_name=f"{row['bureau']}_{row['account_number']}.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.warning(f"No PDF found for {row['account_number']}")

    except Exception as e:
        st.error(f"Error loading DB: {e}")

elif action == "Send New Batch":
    st.subheader("🚀 Send New Dispute Batch")
    st.write("This will generate and mail all new letters from your CSV file.")
    if st.button("Send Now"):
        with st.spinner("Sending batch..."):
            run_command(["python3", "main.py"])
        st.success("Batch process complete! Refresh the dashboard to see updates.")

elif action == "Check Statuses":
    st.subheader("📡 Check Delivery Statuses")
    st.write("This will poll Lob for current letter delivery status and update your DB.")
    if st.button("Check Now"):
        with st.spinner("Checking status..."):
            run_command(["python3", "main.py", "--check-status"])
        st.success("Status update complete! Refresh dashboard to view new statuses.")

elif action == "Add New Dispute":
    st.subheader("📝 Add New Dispute")
    with st.form("new_dispute_form"):
        bureau = st.selectbox("Credit Bureau", ["Experian", "Equifax", "TransUnion"])
        creditor = st.text_input("Creditor Name")
        account = st.text_input("Account Number")
        reason = st.text_area("Dispute Reason")
        submitted = st.form_submit_button("Add to Queue")
        if submitted:
            if not all([bureau, creditor, account, reason]):
                st.warning("All fields are required.")
            else:
                append_to_csv({
                    "bureau": bureau,
                    "creditor_name": creditor,
                    "account_number": account,
                    "reason": reason,
                    "status": "pending",
                    "date_added": datetime.utcnow().strftime("%Y-%m-%d")
                })
                st.success(f"Added new {bureau} dispute for {creditor}.")
