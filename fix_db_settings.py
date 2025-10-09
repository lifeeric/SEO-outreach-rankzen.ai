#!/usr/bin/env python3
"""
Script to fix database settings to use correct values
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_control_panel import app, db, Settings
from app.config import config

def fix_db_settings():
    """Fix database settings to use correct values"""
    print("Fixing database settings...")
    
    with app.app_context():
        settings = Settings.query.first()
        if settings:
            print("Current database settings:")
            print(f"  Resend API Key: '{settings.resend_api_key}'")
            
            # Update with the correct value from environment
            if config.RESEND_API_KEY:
                settings.resend_api_key = config.RESEND_API_KEY
                db.session.commit()
                print(f"Updated Resend API Key to: '{settings.resend_api_key}'")
            else:
                print("No environment variable found for RESEND_API_KEY")
        else:
            print("No settings found in database")

if __name__ == "__main__":
    fix_db_settings()