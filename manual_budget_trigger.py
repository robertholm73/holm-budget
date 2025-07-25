#!/usr/bin/env python3
"""
Manual budget population script for August 2025
This script calls the Render app's admin endpoint to trigger budget population
"""

import json
import requests

def load_settings():
    """Load settings from config file"""
    try:
        with open('config/settings.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: config/settings.json not found")
        return None
    except json.JSONDecodeError:
        print("Error: config/settings.json is not valid JSON")
        return None

def populate_budget_manual():
    """Trigger budget population via Render app's admin endpoint"""
    try:
        # Get the Render app URL
        render_url = input("Enter your Render app URL (e.g., https://your-app.onrender.com): ").strip()
        if not render_url:
            print("Error: No URL provided")
            return False
        
        if not render_url.startswith('http'):
            render_url = 'https://' + render_url
            
        endpoint = f"{render_url}/admin/populate_budget"
        
        print(f"Triggering budget population at: {endpoint}")
        
        # Make POST request to trigger budget population
        response = requests.post(endpoint, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result}")
            
            if result.get('status') == 'success':
                print("\n✅ Budget population completed successfully!")
                return True
            else:
                print(f"\n❌ Budget population failed: {result.get('message', 'Unknown error')}")
                return False
        else:
            print(f"\n❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Manual Budget Population Script")
    print("=" * 40)
    
    success = populate_budget_manual()
    if success:
        print("\n✅ Budget population completed successfully!")
    else:
        print("\n❌ Budget population failed!")