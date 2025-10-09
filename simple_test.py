#!/usr/bin/env python3
"""
Simple test script for email functionality
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_email_functionality():
    """Test the email functionality"""
    print("Testing email functionality...")
    
    # Import the email sender
    from app.email_sender import email_sender
    
    print("Email sender imported successfully")
    print(f"API Key configured: {bool(email_sender.api_key)}")
    
    # Test the check_follow_ups function
    from app.email_sender import check_follow_ups
    print("check_follow_ups function imported successfully")

if __name__ == "__main__":
    test_email_functionality()