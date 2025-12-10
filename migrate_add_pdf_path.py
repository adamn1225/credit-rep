"""
Migration: Add pdf_path column to disputes table
This allows us to cache generated PDFs instead of regenerating them
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/nextcredit')

# Railway provides postgres:// but psycopg2 needs postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

print(f"Connecting to: {DATABASE_URL[:30]}...")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("Adding pdf_path column to disputes table...")
    
    # Add pdf_path column
    cursor.execute("""
        ALTER TABLE disputes 
        ADD COLUMN IF NOT EXISTS pdf_path TEXT
    """)
    
    conn.commit()
    print("✅ Added pdf_path column")
    
    print("\n✅ Migration complete!")
    
except Exception as e:
    print(f"❌ Migration failed: {e}")
    if conn:
        conn.rollback()
finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
