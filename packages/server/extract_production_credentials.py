#!/usr/bin/env python3
"""
Script to extract Google Calendar credentials for production deployment.

This script helps you get the credentials data needed for Railway environment variables.
"""

import json
import pickle
import os
from pathlib import Path


def extract_credentials():
    """Extract credentials for production deployment."""
    
    print("🔧 Google Calendar Production Credentials Extractor")
    print("=" * 50)
    
    # Check if credentials files exist
    creds_file = "google_calendar_credentials.json"
    token_file = "token.pickle"
    
    if not os.path.exists(creds_file):
        print(f"❌ {creds_file} not found!")
        print("   Please run the Google Calendar setup first.")
        return
    
    if not os.path.exists(token_file):
        print(f"❌ {token_file} not found!")
        print("   Please complete the OAuth flow first (run the server locally).")
        return
    
    try:
        # Read the original credentials file
        with open(creds_file, 'r') as f:
            original_creds = json.load(f)
        
        # Read the token pickle to get refresh token
        with open(token_file, 'rb') as f:
            token_data = pickle.load(f)
        
        # Create production credentials JSON
        production_creds = {
            "client_id": original_creds["installed"]["client_id"],
            "client_secret": original_creds["installed"]["client_secret"],
            "refresh_token": token_data.refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "type": "oauth2"
        }
        
        print("✅ Successfully extracted credentials!")
        print("\n🚀 Add this to your Railway environment variables:")
        print("=" * 50)
        print("Variable Name: GOOGLE_CALENDAR_CREDENTIALS_JSON")
        print("Variable Value:")
        print(json.dumps(production_creds, indent=2))
        
        print("\n📋 Other required environment variables:")
        print("=" * 50)
        print("ENVIRONMENT=production")
        print("GOOGLE_CALENDAR_CREDENTIALS_PATH=")  # Leave empty for production
        print(f"WEATHER_API_KEY=your_openweathermap_key")
        print(f"ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key")
        
        print("\n🔒 Security Notes:")
        print("=" * 50)
        print("✅ Never commit these credentials to git")
        print("✅ Store them securely in Railway environment variables")
        print("✅ The refresh token allows automatic token renewal")
        
        # Save to a temporary file for easy copying
        with open("production_credentials.json", "w") as f:
            json.dump(production_creds, f, indent=2)
        
        print(f"\n💾 Credentials also saved to: production_credentials.json")
        print("   (Remember to delete this file after use!)")
        
    except Exception as e:
        print(f"❌ Error extracting credentials: {e}")


if __name__ == "__main__":
    extract_credentials()
