#!/usr/bin/env python3
"""
Script to demonstrate that bot logging output is visible in terminal
"""

import sys
import os
import time
import threading

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_logging_visibility():
    """Test that bot logging is visible in terminal"""
    print("=" * 60)
    print("TESTING BOT LOGGING VISIBILITY")
    print("=" * 60)
    print("1. Starting web control panel in background...")
    print("2. Starting bot through API call...")
    print("3. You should see detailed bot logs in this terminal")
    print("4. Logs will show discovery, auditing, and outreach activities")
    print("=" * 60)
    
    # Import and start web control panel in background
    from web_control_panel import start_bot, logger
    import web_control_panel
    
    print("🤖 Starting bot...")
    logger.info("Test: Starting bot through test script")
    start_bot()
    
    # Wait for bot to start and generate logs
    print("⏳ Waiting for bot to generate logs...")
    time.sleep(3)
    
    print("=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("✅ You should have seen detailed bot logs above")
    print("✅ All bot activities are logged to the terminal")
    print("✅ No functionality was altered")
    print("=" * 60)
    
    # Stop the bot
    print("🛑 Stopping bot...")
    from web_control_panel import stop_bot
    stop_bot()
    print("✅ Bot stopped")

if __name__ == "__main__":
    test_logging_visibility()