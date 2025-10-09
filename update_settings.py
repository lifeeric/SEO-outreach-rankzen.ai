#!/usr/bin/env python3
"""
Script to update web control panel settings with .env file values
"""

import os
from dotenv import load_dotenv
from web_control_panel import app, db, Settings

# Load environment variables
load_dotenv()

def update_settings():
    """Update database settings with .env values"""
    with app.app_context():
        # Get or create settings
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)

        # Update with .env values
        settings.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        settings.serper_api_key = os.getenv('SERPER_API_KEY', '')
        settings.captcha_api_key = os.getenv('CAPTCHA_API_KEY', '')
        settings.stripe_secret_key = os.getenv('STRIPE_SECRET_KEY', '')
        settings.stripe_publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
        settings.stripe_product_key = os.getenv('STRIPE_PRODUCT_KEY', '')
        settings.target_industries = os.getenv('TARGET_INDUSTRIES', 'landscaping,real_estate,plumbers,hvac,roofers,lawyers')
        settings.target_regions = os.getenv('TARGET_REGIONS', 'New York City,Miami-Dade,Austin,Los Angeles,Phoenix')

        db.session.commit()

        print("Settings updated from .env file:")
        print(f"  OpenAI API Key: {'Set' if settings.openai_api_key else 'Not set'}")
        print(f"  Serper API Key: {'Set' if settings.serper_api_key else 'Not set'}")
        print(f"  Target Industries: {settings.target_industries}")
        print(f"  Target Regions: {settings.target_regions}")

if __name__ == "__main__":
    update_settings()
