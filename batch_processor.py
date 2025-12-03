import sys
from pathlib import Path
from generator import render_letter, generate_pdf
from mailer import send_letter
from db import init_db, get_db_connection
from tracker import check_lob_status

def get_pending_disputes():
    """Get all pending disputes from database across all users"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.*, ua.creditor_name, ua.account_type, ua.balance, ua.notes
        FROM disputes d
        LEFT JOIN user_accounts ua ON d.account_id = ua.id
        WHERE d.status = 'pending'
        ORDER BY d.sent_date
    """)
    disputes = cur.fetchall()
    cur.close()
    conn.close()
    return disputes

def update_dispute_status(dispute_id, tracking_id, status):
    """Update dispute with tracking ID and status"""
    from datetime import datetime
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE disputes 
        SET tracking_id = %s, status = %s, sent_date = %s
        WHERE id = %s
    """, (tracking_id, status, datetime.utcnow().isoformat(), dispute_id))
    
    # Log to history
    cur.execute("""
        INSERT INTO dispute_history (dispute_id, action, new_status, notes)
        VALUES (%s, %s, %s, %s)
    """, (dispute_id, 'sent', status, f'Letter sent via Lob (tracking: {tracking_id})'))
    
    conn.commit()
    cur.close()
    conn.close()

def run_batch():
    print("🚀 Starting dispute batch...")
    init_db()

    disputes = get_pending_disputes()
    
    if not disputes:
        print("⚠️ No pending disputes found.")
        return
    
    print(f"📋 Found {len(disputes)} pending dispute(s)")

    for dispute in disputes:
        try:
            # Prepare account info for letter generation
            account_info = {
                'bureau': dispute['bureau'],
                'creditor_name': dispute['creditor_name'],
                'account_number': dispute['account_number'],
                'reason': dispute['description'],
                'account_type': dispute.get('account_type', ''),
                'balance': dispute.get('balance', ''),
                'notes': dispute.get('notes', '')
            }
            
            # Generate letter content (AI or template)
            letter_text = render_letter(account_info, use_ai=True)
            
            # Generate PDF
            bureau_dir = Path(f"disputes/generated/{dispute['bureau'].lower()}")
            bureau_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = bureau_dir / f"{dispute['account_number']}.pdf"
            generate_pdf(letter_text, pdf_path)
            
            print(f"📄 Generated PDF: {pdf_path}")
            
            # Send via Lob
            desc = f"{dispute['bureau']} dispute – {dispute['creditor_name']} ({dispute['account_number']})"
            tracking_id = send_letter(pdf_path, dispute['bureau'], desc)
            
            if tracking_id:
                update_dispute_status(dispute['id'], tracking_id, 'sent')
                print(f"✅ Sent: {desc} | Tracking: {tracking_id}")
            else:
                update_dispute_status(dispute['id'], 'N/A', 'failed')
                print(f"❌ Failed: {desc}")
                
        except Exception as e:
            print(f"❌ Error processing dispute {dispute['id']}: {e}")
            update_dispute_status(dispute['id'], 'N/A', 'failed')

    print("✅ Batch complete.")

if __name__ == "__main__":
    if "--check-status" in sys.argv:
        check_lob_status()
    else:
        run_batch()
