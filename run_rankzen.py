#!/usr/bin/env python3
"""
🚀 RANKZEN AUTOMATED SEO OUTREACH TOOL
Simple, lightweight tool that finds under-optimized local business websites,
runs quick SEO audits, generates plain-English reports, and submits outreach.

USAGE:
    python run_rankzen.py

This script will:
✅ Check and install dependencies automatically
✅ Verify API keys are configured
✅ Start the automated service
✅ Run continuously without manual intervention
✅ Log everything to CSV files

NO COMPLEX SETUP REQUIRED!
"""

import os
import sys
import subprocess
import asyncio
import time
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ ERROR: Python 3.8+ required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    # Check if requirements.txt exists
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found")
        sys.exit(1)
    
    try:
        # Install dependencies
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed")
        
        # Install Playwright browsers
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                      check=True, capture_output=True)
        print("✅ Playwright browsers installed")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)

def check_env_file():
    """Check if .env file exists and has required keys"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env file not found!")
        print("\n📝 Create a .env file with your API keys:")
        print("   OPENAI_API_KEY=your_openai_key_here")
        print("   SERPER_API_KEY=your_serper_key_here")
        print("   CAPTCHA_API_KEY=your_captcha_key_here (optional)")
        print("   STRIPE_SECRET_KEY=your_stripe_key_here (optional)")
        sys.exit(1)
    
    # Read and check .env file
    with open(env_file, 'r') as f:
        content = f.read()
        
    required_keys = ["OPENAI_API_KEY", "SERPER_API_KEY"]
    missing_keys = []
    
    for key in required_keys:
        if key not in content or f"{key}=" in content and not content.split(f"{key}=")[1].split('\n')[0].strip():
            missing_keys.append(key)
    
    if missing_keys:
        print(f"❌ Missing or empty API keys: {', '.join(missing_keys)}")
        print("   Please update your .env file")
        sys.exit(1)
    
    print("✅ API keys configured")

def create_directories():
    """Create necessary directories"""
    directories = ["data", "logs"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    print("✅ Directories created")

def main():
    """Main function - run the automated service"""
    print("🚀 RANKZEN AUTOMATED SEO OUTREACH TOOL")
    print("=" * 50)
    print("🎯 Simple, lightweight automation")
    print("=" * 50)
    print()
    
    # Setup checks
    check_python_version()
    install_dependencies()
    check_env_file()
    create_directories()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            asyncio.run(run_test_mode())
            return
        elif command == "help":
            show_help()
            return
    
    print()
    print("🚀 Starting automated service...")
    print("   This will run continuously and:")
    print("   • Find local business websites")
    print("   • Run SEO audits")
    print("   • Generate reports")
    print("   • Submit outreach via contact forms")
    print("   • Run every 6 minutes automatically")
    print()
    print("✅ NO MANUAL INTERVENTION REQUIRED!")
    print("✅ NO TERMINAL COMMANDS NEEDED!")
    print("✅ RUNS COMPLETELY AUTONOMOUSLY!")
    print()
    print("   (Press Ctrl+C to stop)")
    print("=" * 50)
    
    # Import and run the automated service
    try:
        from automated_agent import AutomatedOutreachAgent
        agent = AutomatedOutreachAgent()
        asyncio.run(agent.run_continuous(cycle_interval_hours=0.1, max_sites_per_cycle=30))
    except KeyboardInterrupt:
        print("\n🛑 Service stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Check your .env file and try again")

def show_help():
    """Show help information"""
    print("🚀 RANKZEN AUTOMATED SEO OUTREACH TOOL")
    print("=" * 50)
    print()
    print("USAGE:")
    print("  python run_rankzen.py              # Start automated service")
    print("  python run_rankzen.py test         # Run test mode")
    print("  python run_rankzen.py help         # Show this help")
    print()
    print("FEATURES:")
    print("  🎯 Phase 1: Discovery, audit, outreach automation")
    print("  🎯 Phase 2: Client engagement & fulfillment workflow")
    print("  🎯 Integrated: Phase 2 starts automatically after outreach")
    print()
    print("MONITORING:")
    print("  📊 CSV logs: seo_outreach_log.csv")
    print("  📊 JSONL logs: data/audit-*.jsonl") 
    print("  📊 Phase 2 logs: data/phase2_*.jsonl")
    print()



async def run_test_mode():
    """Run test mode for quick verification"""
    print("🧪 TEST MODE")
    print("=" * 50)
    print()
    
    try:
        from automated_agent import AutomatedOutreachAgent
        agent = AutomatedOutreachAgent()
        
        print("Testing automated agent with Phase 2 integration...")
        print("Running single cycle to demonstrate Phase 1 + Phase 2 workflow...")
        print()
        
        result = await agent.run_full_cycle(max_sites=5)
        
        if result['cycle_complete']:
            print("✅ Test cycle successful!")
            print(f"   Sites discovered: {result['sites_discovered']}")
            print(f"   Sites audited: {result['sites_audited']}")
            print(f"   Outreach sent: {result['outreach_sent']}")
            print(f"   Duration: {result['duration_seconds']:.1f} seconds")
            print()
            
            if result['outreach_sent'] > 0:
                print("🎯 Phase 2 workflow triggered for successful outreaches!")
                print("   • Engagement messages sent")
                print("   • Payment links ready")
                print("   • Credential collection prepared")
                print("   • SEO implementation queued")
                print("   • Human QA system activated")
            else:
                print("ℹ️  No low-scoring sites found for outreach")
                print("   (This is normal - tool only contacts sites with SEO issues)")
                
        else:
            print(f"❌ Test cycle failed")
            
    except Exception as e:
        print(f"❌ Test mode error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
