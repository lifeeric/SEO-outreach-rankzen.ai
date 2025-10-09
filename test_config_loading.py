#!/usr/bin/env python3
"""
Script to test config loading
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_control_panel import app, load_settings_into_config
from app.config import config

def test_config_loading():
    """Test config loading"""
    print(f"Before load - Config RESEND_API_KEY: {config.RESEND_API_KEY}")
    
    with app.app_context():
        load_settings_into_config()
    
    print(f"After load - Config RESEND_API_KEY: {config.RESEND_API_KEY}")

if __name__ == "__main__":
    test_config_loading()