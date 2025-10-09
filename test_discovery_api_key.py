#!/usr/bin/env python3
"""
Test script to verify discovery uses fresh API key
"""

from app.discovery import BusinessDiscovery
from app.config import config

print("=== DISCOVERY API KEY TEST ===")
print(f"Config SERPER_API_KEY: {config.SERPER_API_KEY[:10] if config.SERPER_API_KEY else 'None'}...")

# Create discovery instance
discovery = BusinessDiscovery()
print(f"Discovery serper_api_key property: {discovery.serper_api_key[:10] if discovery.serper_api_key else 'None'}...")

print("=== END TEST ===")
