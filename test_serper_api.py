#!/usr/bin/env python3
"""
Test script to verify Serper API key
"""

import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_serper_api():
    """Test the Serper API key"""
    api_key = os.getenv('SERPER_API_KEY')

    if not api_key:
        print("No Serper API key found in .env file")
        return

    print(f"Testing Serper API key: {api_key[:10]}...")

    # Test search query
    url = "https://google.serper.dev/search"
    payload = {
        "q": "test query",
        "num": 1
    }
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")

        if response.status_code == 200:
            print("Serper API key is working!")
        elif response.status_code == 403:
            print("Serper API key is invalid or expired")
            print("   Please check your Serper.dev account and API key")
        else:
            print(f"Unexpected response: {response.status_code}")

    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == "__main__":
    test_serper_api()
