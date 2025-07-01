from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import pg8000
import os
from datetime import datetime, date
import json
import urllib.parse

app = Flask(__name__)
CORS(app, origins=['*'], supports_credentials=False)

# Database connection helper
def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Parse DATABASE_URL for pg8000
    import urllib.parse
    parsed = urllib.parse.urlparse(database_url)
    return pg8000.connect(
        host=parsed.hostname,
        database=parsed.path[1:],  # Remove leading slash
        user=parsed.username,
        password=parsed.password,
        port=parsed.port or 5432
    )

# Initialize database
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Bank accounts table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            account_type VARCHAR(50) NOT NULL,
            balance DECIMAL(10,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Budget categories table  
    cur.execute('''
        CREATE TABLE IF NOT EXISTS budget_categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            budgeted_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            current_balance DECIMAL(10,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Updated purchases table with account linking
    cur.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id SERIAL PRIMARY KEY,
            user_name VARCHAR(255) NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            account_id INTEGER,
            budget_category_id INTEGER,
            description TEXT,
            date TIMESTAMP NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts (id),
            FOREIGN KEY (budget_category_id) REFERENCES budget_categories (id)
        )
    ''')
    
    # Insert default bank accounts if they don't exist
    accounts = [
        ('Bank Account 1', 'bank'),
        ('Bank Account 2', 'bank'), 
        ('Bank Account 3', 'bank'),
        ('Bank Account 4', 'bank'),
        ('Bank Account 5', 'bank'),
        ('Bank Account 6', 'bank')
    ]
    
    for name, acc_type in accounts:
        cur.execute('''
            INSERT INTO accounts (name, account_type, balance) 
            VALUES (%s, %s, 0) ON CONFLICT (name) DO NOTHING
        ''', (name, acc_type))
    
    # Insert default budget categories if they don't exist
    # categories = ['Food', 'Transport', 'Shopping', 'Bills', 'Entertainment', 'Health', 'Other']
    # for category in categories:
    #     cur.execute('''
    #         INSERT INTO budget_categories (name, budgeted_amount, current_balance) 
    #         VALUES (%s, 0, 0) ON CONFLICT (name) DO NOTHING
    #     ''', (category,))
    
    conn.commit()
    conn.close()

# Database initialization moved to lazy loading
def ensure_database():
    """Initialize database if not already done. Called on first request."""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("DATABASE_URL not set - database features unavailable")
            return False
            
        init_db()
        print("Database initialized successfully")
        return True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False

@app.route('/')
def mobile_form():
    return render_template('index.html')

@app.route('/sync_purchases', methods=['POST'])
def sync_purchases():
    try:
        # Ensure database is initialized
        ensure_database()
        
        purchases = request.json
        if not purchases:
            return jsonify({"status": "error", "message": "No purchases to sync"})
        
        conn = get_db_connection()
        cur = conn.cursor()
        synced_count = 0
        
        for purchase in purchases:
            account_id = purchase.get('account_id')
            budget_category_name = purchase.get('category', '')
            amount = float(purchase['amount'])
            
            # Get budget category ID
            budget_category_id = None
            if budget_category_name:
                cur.execute('SELECT id FROM budget_categories WHERE name = %s', (budget_category_name,))
                result = cur.fetchone()
                if result:
                    budget_category_id = result[0]
            
            # Insert purchase
            cur.execute('''
                INSERT INTO purchases (user_name, amount, account_id, budget_category_id, description, date)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (purchase.get('user_name', 'Unknown'), amount, account_id, budget_category_id, 
                  purchase.get('description', ''), purchase['timestamp']))
            
            # Update account balance (withdraw)
            if account_id:
                cur.execute('''
                    UPDATE accounts SET balance = balance - %s WHERE id = %s
                ''', (amount, account_id))
            
            # Update budget category balance (withdraw)
            if budget_category_id:
                cur.execute('''
                    UPDATE budget_categories SET current_balance = current_balance - %s WHERE id = %s
                ''', (amount, budget_category_id))
            
            synced_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "synced": synced_count})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_purchases')
def get_purchases():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT p.id, p.user_name, p.amount, p.description, p.date,
                   a.name as account_name, bc.name as category_name
            FROM purchases p 
            LEFT JOIN accounts a ON p.account_id = a.id
            LEFT JOIN budget_categories bc ON p.budget_category_id = bc.id
            ORDER BY p.date DESC
        ''')
        purchases = cur.fetchall()
        conn.close()
        
        # Convert to list of dictionaries for JSON response
        purchase_list = []
        for p in purchases:
            purchase_list.append({
                'id': p[0],
                'user': p[1],
                'amount': p[2],
                'description': p[3],
                'date': p[4],
                'account_name': p[5],
                'category': p[6]
            })
        
        return jsonify(purchase_list)
    
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/get_accounts')
def get_accounts():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, name, balance FROM accounts ORDER BY name')
        accounts = cur.fetchall()
        conn.close()
        
        account_list = []
        for a in accounts:
            account_list.append({
                'id': a[0],
                'name': a[1],
                'balance': float(a[2])  # Ensure balance is a number
            })
        
        return jsonify(account_list)
    
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/get_budget_categories')
def get_budget_categories():
    try:
        # Ensure database is initialized
        ensure_database()
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all budget categories (the original table design doesn't have period_id)
        cur.execute('''
            SELECT id, name, budgeted_amount, current_balance 
            FROM budget_categories 
            ORDER BY name
        ''')
        
        categories = cur.fetchall()
        conn.close()
        
        category_list = []
        for c in categories:
            budgeted = float(c[2])
            current = float(c[3])
            category_list.append({
                'id': c[0],
                'name': c[1],
                'budgeted_amount': budgeted,
                'current_balance': current,
                'remaining': budgeted - abs(current)  # remaining budget
            })
        
        return jsonify(category_list)
    
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/update_account_balance', methods=['POST'])
def update_account_balance():
    try:
        data = request.json
        account_id = data.get('account_id')
        new_balance = data.get('balance')
        
        if account_id is None or new_balance is None:
            return jsonify({"status": "error", "message": "Missing account_id or balance"})
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('UPDATE accounts SET balance = %s WHERE id = %s', (float(new_balance), account_id))
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": "Account balance updated"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/update_budget_amount', methods=['POST'])
def update_budget_amount():
    try:
        data = request.json
        category_id = data.get('category_id')
        budget_amount = data.get('budget_amount')
        
        if category_id is None or budget_amount is None:
            return jsonify({"status": "error", "message": "Missing category_id or budget_amount"})
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('UPDATE budget_categories SET budgeted_amount = %s WHERE id = %s', 
                    (float(budget_amount), category_id))
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": "Budget amount updated"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# Budget Period Management Endpoints
@app.route('/get_budget_periods')
def get_budget_periods():
    """Get all budget periods with their details."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT id, period_name, start_date, end_date, is_active 
            FROM budget_periods 
            ORDER BY start_date
        ''')
        periods = cur.fetchall()
        conn.close()
        
        period_list = []
        for p in periods:
            period_list.append({
                'id': p[0],
                'period_name': p[1],
                'start_date': p[2].isoformat() if p[2] else None,
                'end_date': p[3].isoformat() if p[3] else None,
                'is_active': p[4]
            })
        
        return jsonify(period_list)
    
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/set_active_period', methods=['POST'])
def set_active_period():
    """Set a specific period as active."""
    try:
        data = request.json
        period_id = data.get('period_id')
        
        if period_id is None:
            return jsonify({"status": "error", "message": "Missing period_id"})
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Deactivate all periods
        cur.execute('UPDATE budget_periods SET is_active = FALSE')
        
        # Activate the specified period
        cur.execute('UPDATE budget_periods SET is_active = TRUE WHERE id = %s', (period_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": "Active period updated"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# @app.route('/create_budget_category', methods=['POST'])
# def create_budget_category():
#     """Create a new budget category for a specific period."""
#     try:
#         data = request.json
#         name = data.get('name')
#         budgeted_amount = data.get('budgeted_amount', 0)
#         period_id = data.get('period_id')
#         
#         if not name:
#             return jsonify({"status": "error", "message": "Category name is required"})
#         
#         conn = get_db_connection()
#         cur = conn.cursor()
#         
#         # If no period_id provided, use current active period
#         if not period_id:
#             cur.execute('SELECT id FROM budget_periods WHERE is_active = TRUE LIMIT 1')
#             result = cur.fetchone()
#             if result:
#                 period_id = result[0]
#             else:
#                 return jsonify({"status": "error", "message": "No active period found"})
#         
#         # Insert new category
#         cur.execute('''
#             INSERT INTO budget_categories (name, budgeted_amount, current_balance, period_id)
#             VALUES (%s, %s, 0, %s)
#         ''', (name, float(budgeted_amount), period_id))
#         
#         conn.commit()
#         conn.close()
#         
#         return jsonify({"status": "success", "message": "Budget category created"})
#     
#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)})

# Transfer endpoints temporarily disabled until migration is run
# @app.route('/get_transfers')
# def get_transfers():
#     """Get all transfers for display."""
#     try:
#         conn = get_db_connection()
#         cur = conn.cursor()
#         cur.execute('''
#             SELECT t.id, t.amount, t.description, t.originator_user, t.transfer_date,
#                    fa.name as from_account_name, ta.name as to_account_name
#             FROM transfers t 
#             LEFT JOIN accounts fa ON t.from_account_id = fa.id
#             LEFT JOIN accounts ta ON t.to_account_id = ta.id
#             ORDER BY t.transfer_date DESC
#         ''')
#         transfers = cur.fetchall()
#         conn.close()
#         
#         transfer_list = []
#         for t in transfers:
#             transfer_list.append({
#                 'id': t[0],
#                 'amount': float(t[1]),
#                 'description': t[2],
#                 'originator': t[3],
#                 'date': t[4].isoformat() if t[4] else None,
#                 'from_account': t[5],
#                 'to_account': t[6]
#             })
#         
#         return jsonify(transfer_list)
#     
#     except Exception as e:
#         return jsonify({"error": str(e)})

# @app.route('/create_transfer', methods=['POST'])
# def create_transfer():
#     """Create a new transfer between accounts."""
#     try:
#         data = request.json
#         from_account_id = data.get('from_account_id')
#         to_account_id = data.get('to_account_id')
#         amount = float(data.get('amount', 0))
#         description = data.get('description', '')
#         originator = data.get('originator', 'Robert')
#         transfer_date = data.get('transfer_date', datetime.now().isoformat())
#         
#         if not from_account_id or not to_account_id or amount <= 0:
#             return jsonify({"status": "error", "message": "Invalid transfer data"})
#         
#         if from_account_id == to_account_id:
#             return jsonify({"status": "error", "message": "Cannot transfer to the same account"})
#         
#         conn = get_db_connection()
#         cur = conn.cursor()
#         
#         # Check source account balance
#         cur.execute('SELECT balance FROM accounts WHERE id = %s', (from_account_id,))
#         result = cur.fetchone()
#         if not result or result[0] < amount:
#             return jsonify({"status": "error", "message": "Insufficient funds"})
#         
#         # Perform transfer
#         cur.execute('UPDATE accounts SET balance = balance - %s WHERE id = %s', 
#                    (amount, from_account_id))
#         cur.execute('UPDATE accounts SET balance = balance + %s WHERE id = %s', 
#                    (amount, to_account_id))
#         
#         # Record transfer
#         cur.execute('''
#             INSERT INTO transfers (from_account_id, to_account_id, amount, description, originator_user, transfer_date)
#             VALUES (%s, %s, %s, %s, %s, %s)
#         ''', (from_account_id, to_account_id, amount, description, originator, transfer_date))
#         
#         conn.commit()
#         conn.close()
#         
#         return jsonify({"status": "success", "message": "Transfer completed"})
#     
#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)})

# Income Management Endpoint
@app.route('/add_income', methods=['POST'])
def add_income():
    """Add income to an account."""
    try:
        # Ensure database is initialized
        ensure_database()
        
        data = request.json
        username = data.get('username', 'Unknown')
        amount = float(data.get('amount', 0))
        target_account_id = data.get('target_account_id')
        description = data.get('description', '')
        income_date = data.get('income_date', datetime.now().isoformat())
        
        if not target_account_id or amount <= 0:
            return jsonify({"status": "error", "message": "Invalid income data"})
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Add income to target account
        cur.execute('UPDATE accounts SET balance = balance + %s WHERE id = %s', 
                   (amount, target_account_id))
        
        # Record the income as a special transaction (negative amount indicates income)
        income_description = f"Income: {description} (received by {username})"
        
        cur.execute('''
            INSERT INTO purchases (user_name, amount, account_id, budget_category_id, description, date)
            VALUES (%s, %s, %s, NULL, %s, %s)
        ''', (username, -amount, target_account_id, income_description, income_date))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": "Income added successfully"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# Migration endpoint removed for security

@app.route('/manifest.json')
def manifest():
    return {
        "name": "Budget Tracker",
        "short_name": "Budget",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#000000",
        "icons": [
            {
                "src": "/static/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            }
        ]
    }

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)