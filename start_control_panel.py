#!/usr/bin/env python3
"""
Simple startup script for the RankZen Web Control Panel
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("🚀 Starting RankZen Web Control Panel...")
    print("📊 Dashboard: http://localhost:8000/admin")
    print("🏠 Landing Page: http://localhost:8000/")
    print("Default admin password: admin123")
    print("Press Ctrl+C to stop")
    print("-" * 50)

    # Import and run the web control panel
    from web_control_panel import app
    app.run(host='0.0.0.0', port=8000, debug=False)

if __name__ == "__main__":
    main()
