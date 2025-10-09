#!/usr/bin/env python3
"""
Script to test settings display functionality
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_control_panel import app, Settings

def test_settings_display():
    """Test settings display functionality"""
    print("Testing settings display functionality...")
    
    with app.app_context():
        settings = Settings.query.first()
        if settings:
            print("Current database settings:")
            print(f"  OpenAI API Key: '{settings.openai_api_key}'")
            print(f"  Serper API Key: '{settings.serper_api_key}'")
            print(f"  Resend API Key: '{settings.resend_api_key}'")
            print(f"  Stripe Secret Key: '{settings.stripe_secret_key}'")
            
            # Check if form would display these values
            print("\nForm would display these values in input fields:")
            print(f"  OpenAI API Key field: '{settings.openai_api_key}'")
            print(f"  Serper API Key field: '{settings.serper_api_key}'")
            print(f"  Resend API Key field: '{settings.resend_api_key}'")
            print(f"  Stripe Secret Key field: '{settings.stripe_secret_key}'")
        else:
            print("No settings found in database")

if __name__ == "__main__":
    test_settings_display()