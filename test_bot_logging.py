#!/usr/bin/env python3
"""
Script to test bot logging functionality
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from automated_agent import AutomatedOutreachAgent
import logging

def test_bot_logging():
    """Test bot logging functionality"""
    print("Testing bot logging functionality...")
    
    # Configure logging to show in terminal
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create bot instance
    bot = AutomatedOutreachAgent()
    
    # Test logging
    bot.logger.info("🧪 Test log message from bot")
    print("✅ Test log message sent")

if __name__ == "__main__":
    test_bot_logging()