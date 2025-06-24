# In your PySide app
import requests

class BudgetManager:
    def __init__(self):
        self.server_url = "https://your-app.railway.app"  # Your cloud URL
        
    def sync_from_server(self):
        try:
            response = requests.get(f"{self.server_url}/get_purchases")
            purchases = response.json()
            # Update your local database
            self.update_local_db(purchases)
        except requests.exceptions.RequestException:
            print("Server not reachable")