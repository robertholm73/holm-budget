# Budget App Setup Guide

## Quick Setup

### 1. Install Dependencies
```bash
pip install flask pyside6 requests matplotlib
```

### 2. Test Locally
```bash
python app.py
# Visit http://localhost:5000 to test mobile interface
python desktop_budget.py  # Test desktop app
```

### 3. Deploy to Railway
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```
Get your URL: `https://your-app-name.railway.app`

### 4. Configure Desktop App
Edit `desktop_budget.py` line 19:
```python
self.server_url = "https://your-app-name.railway.app"  # Your Railway URL
```

### 5. Setup Mobile App
- Send Railway URL to your wife
- On her phone: Open URL → Add to Home Screen
- Works offline, syncs when online

## Initial Configuration

### Desktop App (Your Laptop)
1. Run `python desktop_budget.py`
2. **Accounts Tab:**
   - Set initial balances for your 6 bank accounts
   - Set budget amounts for categories (Food, Transport, etc.)
3. Use other tabs for analysis and manual transactions

### Mobile App (Wife's Phone)
- Select account for each purchase
- Choose category and enter amount
- Works offline, syncs automatically

## Key Features

**6 Bank Accounts** with real-time balance tracking
**Budget Categories** with spending limits and progress bars
**Offline Mobile** capability with automatic sync
**Real-time Analytics** on desktop app

## Database Access (Railway)
```bash
railway run sqlite3 budget.db
```

## Currency
All amounts display in South African Rand (R).

Your budget app is ready! Wife tracks expenses anywhere, you get powerful analysis tools.