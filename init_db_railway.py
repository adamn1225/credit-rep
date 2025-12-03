#!/usr/bin/env python3
"""Initialize database on Railway - run this once after deployment"""
from db import init_db

if __name__ == '__main__':
    print("Initializing database...")
    init_db()
    print("✅ Database initialized successfully!")
