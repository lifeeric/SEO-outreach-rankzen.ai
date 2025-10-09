#!/usr/bin/env python3
"""
Script to test settings update functionality
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_control_panel import app, db, Settings, load_settings_into_config
from app.config import config
from app.email_sender import email_sender

def test_settings_update():
    """Test settings update functionality"""
    print("Testing settings update functionality...")
    
    # Check initial state
    print(f"Initial ENV RESEND_API_KEY: {config.RESEND_API_KEY}")
    
    with app.app_context():
        # Load settings from database
        load_settings_into_config()
        print(f"After loading DB settings: {config.RESEND_API_KEY}")
        
        # Check email sender API key
        print(f"Email sender API key: {email_sender.api_key}")
        
        # Simulate updating settings through admin interface
        settings = Settings.query.first()
        if settings:
            # Save original value
            original_resend_key = settings.resend_api_key
            
            # Update with a new test value
            settings.resend_api_key = "test_new_key_12345"
            db.session.commit()
            
            # Reload settings
            load_settings_into_config()
            print(f"After updating DB and reloading: {config.RESEND_API_KEY}")
            print(f"Email sender API key after update: {email_sender.api_key}")
            
            # Restore original value
            settings.resend_api_key = original_resend_key
            db.session.commit()
            
            # Reload settings again
            load_settings_into_config()
            print(f"After restoring original DB value: {config.RESEND_API_KEY}")
            print(f"Email sender API key after restore: {email_sender.api_key}")
        else:
            print("No settings found in database")

if __name__ == "__main__":
    test_settings_update()