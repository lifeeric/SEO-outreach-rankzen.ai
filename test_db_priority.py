#!/usr/bin/env python3
"""
Script to test database priority when env is empty
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_control_panel import app, Settings, load_settings_into_config
from app.config import config

def test_db_priority():
    """Test that database values are used when env is empty"""
    print("Testing database priority when env is empty...")
    
    # Save original env value
    original_env_key = config.RESEND_API_KEY
    print(f"Original ENV RESEND_API_KEY: {original_env_key}")
    
    # Temporarily clear the environment variable
    config.RESEND_API_KEY = ""
    print(f"ENV RESEND_API_KEY after clearing: '{config.RESEND_API_KEY}'")
    
    with app.app_context():
        # Load settings from database
        load_settings_into_config()
        print(f"Config RESEND_API_KEY after loading DB settings: '{config.RESEND_API_KEY}'")
        
        # Check if database value is used when env is empty
        if config.RESEND_API_KEY and config.RESEND_API_KEY != original_env_key:
            print("✓ Database value correctly used when env is empty")
        else:
            print("✗ Database value not used when env is empty")
    
    # Restore original env value
    config.RESEND_API_KEY = original_env_key
    print(f"ENV RESEND_API_KEY after restoring: {config.RESEND_API_KEY}")

if __name__ == "__main__":
    test_db_priority()