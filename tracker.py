import lob
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()
lob.api_key = os.getenv("LOB_API_KEY")

DB_PATH = "disputes.db"

def fetch_pending_disputes():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, tracking_id, description FROM disputes WHERE status IN ('sent', 'in_transit', 'queued')")
    rows = c.fetchall()
    conn.close()
    return rows

def update_status(dispute_id, new_status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE disputes SET status = ? WHERE id = ?", (new_status, dispute_id))
    conn.commit()
    conn.close()

def check_lob_status():
    print("📡 Checking Lob letter delivery statuses...")
    pending = fetch_pending_disputes()

    if not pending:
        print("✅ No pending letters found.")
        return

    for dispute_id, tracking_id, description in pending:
        try:
            if not tracking_id or tracking_id == "N/A":
                update_status(dispute_id, "invalid_tracking_id")
                print(f"⚠️ Skipping {description}: invalid tracking ID")
                continue

            letter = lob.Letter.retrieve(tracking_id)
            current_status = letter.get("status", "unknown")
            update_status(dispute_id, current_status)
            print(f"🔄 {description}: {current_status}")

        except Exception as e:
            print(f"❌ Error checking {description}: {e}")

    print("✅ Status check complete.")
