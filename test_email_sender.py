#!/usr/bin/env python3
"""
Test script for the email sender functionality
"""

import os
import sys
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Load environment variables
load_dotenv()

from app.email_sender import email_sender
from app.models import BusinessSite, OutreachMessage

def test_email_sending():
    """Test the email sending functionality"""
    print("Testing email sending functionality...")
    
    # Check if Resend API key is configured
    if not email_sender.api_key:
        print("❌ Resend API key not configured. Please set RESEND_API_KEY in your .env file")
        return False
    
    # Create test data
    site = BusinessSite(
        url="https://example.com",
        domain="example.com",
        business_name="Test Business"
    )
    
    message = OutreachMessage(
        subject="Test Email from Rankzen",
        message="This is a test email sent from the Rankzen SEO automation tool."
    )
    
    # For testing, you can use your own email address
    test_email = os.getenv("TEST_EMAIL", "jaspython8@gmail.com")
    
    print(f"Sending test email to: {test_email}")
    
    # Send the email
    success = email_sender.send_outreach_email(site, message, test_email)
    
    if success:
        print("✅ Email sent successfully!")
        return True
    else:
        print("❌ Failed to send email")
        return False

if __name__ == "__main__":
    test_email_sending()