#!/usr/bin/env python3
"""Initialize Railway PostgreSQL database"""

import os
from db import init_db, get_db_connection

print("🔄 Initializing Railway database...")

try:
    # Initialize database schema
    init_db()
    print("✅ Database schema created successfully!")
    
    # Verify tables exist
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    
    print(f"\n📋 Created tables ({len(tables)}):")
    for table in tables:
        print(f"  - {table[0]}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
