#!/usr/bin/env python3
"""Test login functionality and database connection"""

import os
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:fnJqTSwcMseGRyZFsPcXtBHVPgXjNoxs@metro.proxy.rlwy.net:55680/railway')

from db import get_db_connection, get_user_by_email, create_user_with_email
from werkzeug.security import check_password_hash

print("🔍 Testing database connection and login...")

try:
    # Test connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if users table exists
    cursor.execute("SELECT COUNT(*) FROM users")
    result = cursor.fetchone()
    print(f"✅ Users table exists. Total users: {result['count']}")
    
    # List all users
    cursor.execute("SELECT id, email, username, role, is_active FROM users")
    users = cursor.fetchall()
    print(f"\n📋 Existing users:")
    for user in users:
        print(f"  - {user['email']} (username: {user['username']}, role: {user['role']}, active: {user['is_active']})")
    
    cursor.close()
    conn.close()
    
    # Test creating a test user if none exist
    if len(users) == 0:
        print("\n🆕 No users found. Creating test user...")
        success, msg = create_user_with_email(
            email='test@example.com',
            password='test123',
            first_name='Test',
            last_name='User',
            phone='',
            agree_tos=True,
            marketing_emails=False,
            role='user'
        )
        print(f"Create user result: {success} - {msg}")
    
    # Test login with first user
    if len(users) > 0:
        test_email = users[0]['email']
        print(f"\n🔐 Testing get_user_by_email with: {test_email}")
        user = get_user_by_email(test_email)
        if user:
            print(f"✅ User found: {user['email']}")
            print(f"   - id: {user['id']}")
            print(f"   - username: {user.get('username')}")
            print(f"   - role: {user.get('role')}")
            print(f"   - has password_hash: {'password_hash' in user}")
        else:
            print(f"❌ User not found!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
