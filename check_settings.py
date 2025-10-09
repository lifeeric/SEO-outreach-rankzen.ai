#!/usr/bin/env python3
"""
Script to check current settings in the database
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_control_panel import app, db, Settings

def check_settings():
    """Check current settings in the database"""
    with app.app_context():
        settings = Settings.query.first()
        if settings:
            print("Current Database Settings:")
            print(f"  OpenAI API Key: {settings.openai_api_key}")
            print(f"  Serper API Key: {settings.serper_api_key}")
            print(f"  Captcha API Key: {settings.captcha_api_key}")
            print(f"  Resend API Key: {settings.resend_api_key}")
            print(f"  Stripe Secret Key: {settings.stripe_secret_key}")
            print(f"  Stripe Publishable Key: {settings.stripe_publishable_key}")
            print(f"  Stripe Product Key: {settings.stripe_product_key}")
            print(f"  Target Industries: {settings.target_industries}")
            print(f"  Target Regions: {settings.target_regions}")
        else:
            print("No settings found in database")

if __name__ == "__main__":
    check_settings()