#!/usr/bin/env python3
"""
Script to check the database contents
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import directly from web_control_panel to avoid circular imports
from web_control_panel import app, db

def check_database():
    """Check the database contents"""
    with app.app_context():
        # Import EmailOutreach inside the app context
        from web_control_panel import EmailOutreach, Lead, Settings
        
        print("=== Database Contents ===")
        
        # Check Settings table
        settings_count = Settings.query.count()
        print(f"Settings records: {settings_count}")
        
        # Check Lead table
        lead_count = Lead.query.count()
        print(f"Lead records: {lead_count}")
        
        # Check EmailOutreach table
        email_records = EmailOutreach.query.all()
        print(f"EmailOutreach records: {len(email_records)}")
        
        for record in email_records:
            print(f"  - ID: {record.id}")
            print(f"    Recipient: {record.recipient_email}")
            print(f"    Domain: {record.domain}")
            print(f"    Campaign Type: {record.campaign_type}")
            print(f"    Status: {record.status}")
            print(f"    Message ID: {record.message_id}")
            print(f"    Sent At: {record.sent_at}")
            print(f"    Follow-up Sent: {record.follow_up_sent}")
            print(f"    Follow-up Message ID: {record.follow_up_message_id}")
            print()

if __name__ == "__main__":
    check_database()