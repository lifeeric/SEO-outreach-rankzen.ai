#!/usr/bin/env python3
"""
Script to check the Resend API key in the database
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_control_panel import app, Settings

def check_db_key():
    """Check the Resend API key in the database"""
    with app.app_context():
        settings = Settings.query.first()
        if settings:
            print(f"DB RESEND_API_KEY: '{settings.resend_api_key}'")
            print(f"DB RESEND_API_KEY length: {len(settings.resend_api_key) if settings.resend_api_key else 0}")
        else:
            print("No settings found in database")

if __name__ == "__main__":
    check_db_key()