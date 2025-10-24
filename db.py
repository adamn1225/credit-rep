import sqlite3
from datetime import datetime

DB_PATH = "disputes.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS disputes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT,
            bureau TEXT,
            description TEXT,
            sent_date TEXT,
            tracking_id TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_dispute(account_number, bureau, description, tracking_id, status="sent"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO disputes (account_number, bureau, description, sent_date, tracking_id, status) VALUES (?, ?, ?, ?, ?, ?)",
        (account_number, bureau, description, datetime.utcnow().isoformat(), tracking_id, status)
    )
    conn.commit()
    conn.close()
