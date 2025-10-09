#!/usr/bin/env python3
"""
Script to test encryption functionality
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_control_panel import app, db, Settings

def test_encryption():
    """Test encryption functionality"""
    print("Testing encryption functionality...")
    
    with app.app_context():
        # Create or get settings object
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
            db.session.commit()
        
        # Test encrypting a sample API key
        test_key = "sk-test-1234567890abcdef"
        encrypted = settings.encrypt_value(test_key)
        decrypted = settings.decrypt_value(encrypted)
        
        print(f"Original: {test_key}")
        print(f"Encrypted: {encrypted}")
        print(f"Decrypted: {decrypted}")
        print(f"Match: {test_key == decrypted}")
        
        # Test with empty value
        empty_encrypted = settings.encrypt_value("")
        empty_decrypted = settings.decrypt_value(empty_encrypted)
        print(f"Empty value test - Encrypted: '{empty_encrypted}', Decrypted: '{empty_decrypted}'")

if __name__ == "__main__":
    test_encryption()