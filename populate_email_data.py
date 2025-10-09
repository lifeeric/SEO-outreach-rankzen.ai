#!/usr/bin/env python3
"""
Script to populate sample email data for testing the email outreach dashboard
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_control_panel import app, db, EmailOutreach

def populate_sample_data():
    """Populate sample email data for testing"""
    with app.app_context():
        # Clear existing email data for clean test
        EmailOutreach.query.delete()
        
        # Add sample outreach emails
        for i in range(5):
            email = EmailOutreach(
                message_id=f"msg_{i}",
                recipient_email=f"user{i}@example.com",
                domain=f"example{i}.com",
                campaign_type="outreach",
                status="sent",
                sent_at=datetime.utcnow() - timedelta(days=i),
                follow_up_sent=(i % 2 == 0)  # Every other one has follow-up sent
            )
            db.session.add(email)
        
        # Add sample follow-up emails
        for i in range(3):
            email = EmailOutreach(
                message_id=f"followup_{i}",
                recipient_email=f"user{i}@example.com",
                domain=f"example{i}.com",
                campaign_type="follow-up",
                status="sent",
                sent_at=datetime.utcnow() - timedelta(days=i*2),
                follow_up_sent=False
            )
            db.session.add(email)
        
        # Add some pending follow-ups (outreach emails from 4+ days ago with no follow-up)
        for i in range(2):
            email = EmailOutreach(
                message_id=f"pending_{i}",
                recipient_email=f"pending{i}@example.com",
                domain=f"pending{i}.com",
                campaign_type="outreach",
                status="sent",
                sent_at=datetime.utcnow() - timedelta(days=4+i),
                follow_up_sent=False
            )
            db.session.add(email)
        
        db.session.commit()
        print("Sample email data populated successfully!")

if __name__ == "__main__":
    populate_sample_data()