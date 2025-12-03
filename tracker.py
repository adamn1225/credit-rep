import lob
import os
from dotenv import load_dotenv
from db import get_db_connection

load_dotenv()
lob.api_key = os.getenv("LOB_API_KEY")

def fetch_pending_disputes():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, tracking_id, description FROM disputes WHERE status IN ('sent', 'in_transit', 'queued')")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def update_status(dispute_id, new_status):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE disputes SET status = %s WHERE id = %s", (new_status, dispute_id))
    conn.commit()
    cur.close()
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
