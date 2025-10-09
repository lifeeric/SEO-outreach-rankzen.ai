#!/usr/bin/env python3
"""
Test script for email follow-up functionality
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.email_sender import email_sender, check_follow_ups
from app.models import BusinessSite, OutreachMessage
from web_control_panel import app, db, EmailOutreach

def test_email_sending_and_follow_up():
    """Test the email sending and follow-up functionality"""
    
    with app.app_context():
        # Create a test business site
        site = BusinessSite(
            url="https://example.com",
            domain="example.com",
            business_name="Test Business"
        )
        
        # Create a test outreach message
        message = OutreachMessage(
            subject="Test Subject",
            message="This is a test message for email follow-up functionality."
        )
        
        # Test sending an outreach email
        print("Testing email sending...")
        result = email_sender.send_outreach_email(site, message, "test@example.com", "outreach")
        print(f"Email sending result: {result}")
        
        # Check if the email record was created
        email_record = EmailOutreach.query.filter_by(recipient_email="test@example.com").first()
        if email_record:
            print(f"Email record created: {email_record}")
        else:
            print("No email record found")
            
        # Test follow-up checking
        print("\nTesting follow-up checking...")
        check_follow_ups()
        print("Follow-up check completed")

if __name__ == "__main__":
    test_email_sending_and_follow_up()