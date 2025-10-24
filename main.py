import sys
from generator import build_letters
from mailer import send_letter
from db import init_db, log_dispute
from tracker import check_lob_status

def run_batch():
    print("🚀 Starting dispute batch...")
    init_db()

    letters = build_letters()

    for pdf_path, row in letters:
        desc = f"{row['bureau']} dispute – {row['creditor_name']} ({row['account_number']})"
        tracking_id = send_letter(pdf_path, row["bureau"], desc)
        if tracking_id:
            log_dispute(row["account_number"], row["bureau"], desc, tracking_id)
        else:
            log_dispute(row["account_number"], row["bureau"], desc, "N/A", status="failed")

    print("✅ Batch complete.")

if __name__ == "__main__":
    if "--check-status" in sys.argv:
        check_lob_status()
    else:
        run_batch()
