#!/usr/bin/env python3
"""
Script to test the full system with encryption and dynamic config updates
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_control_panel import app, db, Settings, load_settings_into_config
from app.config import config

def test_full_system():
    """Test the full system with encryption and dynamic config updates"""
    print("Testing full system with encryption and dynamic config updates...")
    
    with app.app_context():
        # Create or get settings object
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
            db.session.commit()
        
        # Test storing an API key
        test_api_key = "sk-test-full-system-1234567890"
        settings.openai_api_key = settings.encrypt_value(test_api_key)
        db.session.commit()
        
        print(f"Stored encrypted API key: {settings.openai_api_key}")
        
        # Test loading settings into config
        load_settings_into_config()
        
        print(f"Config after loading: {config.OPENAI_API_KEY}")
        print(f"Match: {config.OPENAI_API_KEY == test_api_key}")
        
        # Test updating with a new key
        new_api_key = "sk-test-new-key-0987654321"
        settings.openai_api_key = settings.encrypt_value(new_api_key)
        db.session.commit()
        
        # Reload config
        load_settings_into_config()
        
        print(f"Config after update: {config.OPENAI_API_KEY}")
        print(f"Match: {config.OPENAI_API_KEY == new_api_key}")

if __name__ == "__main__":
    test_full_system()