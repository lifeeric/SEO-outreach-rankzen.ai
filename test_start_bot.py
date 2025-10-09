#!/usr/bin/env python3
"""
Script to test starting the bot and verifying logging output
"""

import sys
import os
import time

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_control_panel import start_bot, bot_running

def test_start_bot():
    """Test starting the bot and verifying logging output"""
    print("Testing bot start functionality...")
    
    # Start the bot
    print("Starting bot...")
    start_bot()
    
    # Wait a moment for the bot to start
    time.sleep(2)
    
    # Check if bot is running
    print(f"Bot running status: {bot_running}")
    
    if bot_running:
        print("✅ Bot started successfully")
        print("📝 Check the terminal where web_control_panel.py is running for detailed logs")
        print("⏳ Bot will run for 10 seconds, then stop...")
        
        # Let it run for a bit to generate logs
        time.sleep(10)
        
        print("🛑 Stopping bot...")
        from web_control_panel import stop_bot
        stop_bot()
        print("✅ Bot stopped")
    else:
        print("❌ Failed to start bot")

if __name__ == "__main__":
    test_start_bot()