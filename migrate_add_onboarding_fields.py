"""
Migration: Add onboarding fields to users table
Adds: date_of_birth, ssn_last_4, profile_completed
"""
import psycopg2
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/nextcredit')

# Railway provides postgres:// but psycopg2 needs postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

print(f"Connecting to: {DATABASE_URL[:30]}...")

conn = psycopg2.connect(DATABASE_URL)
c = conn.cursor()

print("Adding onboarding columns to users table...")

# Add columns if they don't exist
try:
    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS date_of_birth DATE")
    print("✅ Added date_of_birth column")
except Exception as e:
    print(f"⚠️  date_of_birth: {e}")

try:
    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ssn_last_4 TEXT")
    print("✅ Added ssn_last_4 column")
except Exception as e:
    print(f"⚠️  ssn_last_4: {e}")

try:
    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_completed BOOLEAN DEFAULT FALSE")
    print("✅ Added profile_completed column")
except Exception as e:
    print(f"⚠️  profile_completed: {e}")

conn.commit()
conn.close()

print("\n✅ Migration complete!")
