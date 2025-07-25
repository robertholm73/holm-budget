#!/usr/bin/env python3
"""
Trigger August 2025 budget population on Render
"""

import requests
import sys

def trigger_budget_population(render_url):
    """Trigger budget population via Render app's admin endpoint"""
    try:
        if not render_url.startswith('http'):
            render_url = 'https://' + render_url
            
        endpoint = f"{render_url}/admin/populate_budget"
        
        print(f"Triggering budget population at: {endpoint}")
        
        # Make POST request
        response = requests.post(endpoint, timeout=30)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print("\n✅ Budget population completed successfully!")
                return True
            else:
                print(f"\n❌ Budget population failed: {result.get('message', 'Unknown error')}")
                return False
        else:
            print(f"\n❌ Request failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 trigger_august_budget.py <your-render-url>")
        print("Example: python3 trigger_august_budget.py https://your-app.onrender.com")
        sys.exit(1)
    
    render_url = sys.argv[1]
    print("August 2025 Budget Population Trigger")
    print("=" * 40)
    
    success = trigger_budget_population(render_url)
    if not success:
        sys.exit(1)