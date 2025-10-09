#!/usr/bin/env python3
"""
Test script to verify config reloading
"""

from app.config import config
from web_control_panel import load_settings_into_config

print("=== CONFIG RELOAD TEST ===")
print(f"Initial SERPER_API_KEY: {config.SERPER_API_KEY[:10] if config.SERPER_API_KEY else 'None'}...")
print(f"Initial OPENAI_API_KEY: {config.OPENAI_API_KEY[:10] if config.OPENAI_API_KEY else 'None'}...")

# Simulate loading settings
load_settings_into_config()

print(f"After reload SERPER_API_KEY: {config.SERPER_API_KEY[:10] if config.SERPER_API_KEY else 'None'}...")
print(f"After reload OPENAI_API_KEY: {config.OPENAI_API_KEY[:10] if config.OPENAI_API_KEY else 'None'}...")

print("=== END TEST ===")
