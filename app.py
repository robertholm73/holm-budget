from flask import Flask, request, jsonify, render_template, send_from_directory
import psycopg2
import psycopg2.extras
import os
from datetime import datetime
import json
import urllib.parse

app = Flask(__name__)

# Database connection helper
def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Parse the DATABASE_URL for Render
        parsed = urllib.parse.urlparse(database_url)
        return psycopg2.connect(
            host=parsed.hostname,
            database=parsed.path[1:],  # Remove leading slash
            user=parsed.username,
            password=parsed.password,
            port=parsed.port
        )
    else:
        # Local development fallback
        return psycopg2.connect(
            host='localhost',
            database='holm_budget_database',
            user='postgres',
            password='password',
            port=5432
        )

# Initialize database
def init_db():
    conn = get_db_connection()
    
    # Bank accounts table
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            account_type VARCHAR(50) NOT NULL,
            balance DECIMAL(10,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Budget categories table  
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budget_categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            budgeted_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            current_balance DECIMAL(10,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Updated purchases table with account linking
    cursor.execute('''
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
        cursor.execute('''
            INSERT INTO accounts (name, account_type, balance) 
            VALUES (%s, %s, 0) ON CONFLICT (name) DO NOTHING
        ''', (name, acc_type))
    
    # Insert default budget categories if they don't exist
    categories = ['Food', 'Transport', 'Shopping', 'Bills', 'Entertainment', 'Health', 'Other']
    for category in categories:
        cursor.execute('''
            INSERT INTO budget_categories (name, budgeted_amount, current_balance) 
            VALUES (%s, 0, 0) ON CONFLICT (name) DO NOTHING
        ''', (category,))
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

@app.route('/')
def mobile_form():
    return render_template('index.html')

@app.route('/sync_purchases', methods=['POST'])
def sync_purchases():
    try:
        purchases = request.json
        if not purchases:
            return jsonify({"status": "error", "message": "No purchases to sync"})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        synced_count = 0
        
        for purchase in purchases:
            account_id = purchase.get('account_id')
            budget_category_name = purchase.get('category', '')
            amount = float(purchase['amount'])
            
            # Get budget category ID
            budget_category_id = None
            if budget_category_name:
                cursor.execute('SELECT id FROM budget_categories WHERE name = %s', (budget_category_name,))
                result = cursor.fetchone()
                if result:
                    budget_category_id = result[0]
            
            # Insert purchase
            cursor.execute('''
                INSERT INTO purchases (user_name, amount, account_id, budget_category_id, description, date)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', ('wife', amount, account_id, budget_category_id, 
                  purchase.get('description', ''), purchase['timestamp']))
            
            # Update account balance (withdraw)
            if account_id:
                cursor.execute('''
                    UPDATE accounts SET balance = balance - %s WHERE id = %s
                ''', (amount, account_id))
            
            # Update budget category balance (withdraw)
            if budget_category_id:
                cursor.execute('''
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
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.id, p.user_name, p.amount, p.description, p.date,
                   a.name as account_name, bc.name as category_name
            FROM purchases p 
            LEFT JOIN accounts a ON p.account_id = a.id
            LEFT JOIN budget_categories bc ON p.budget_category_id = bc.id
            ORDER BY p.date DESC
        ''')
        purchases = cursor.fetchall()
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
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, balance FROM accounts ORDER BY name')
        accounts = cursor.fetchall()
        conn.close()
        
        account_list = []
        for a in accounts:
            account_list.append({
                'id': a[0],
                'name': a[1],
                'balance': a[2]
            })
        
        return jsonify(account_list)
    
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/get_budget_categories')
def get_budget_categories():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, budgeted_amount, current_balance FROM budget_categories ORDER BY name')
        categories = cursor.fetchall()
        conn.close()
        
        category_list = []
        for c in categories:
            category_list.append({
                'id': c[0],
                'name': c[1],
                'budgeted_amount': c[2],
                'current_balance': c[3],
                'remaining': c[2] - abs(c[3])  # remaining budget
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
        cursor = conn.cursor()
        cursor.execute('UPDATE accounts SET balance = %s WHERE id = %s', (float(new_balance), account_id))
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
        cursor = conn.cursor()
        cursor.execute('UPDATE budget_categories SET budgeted_amount = %s WHERE id = %s', 
                    (float(budget_amount), category_id))
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": "Budget amount updated"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

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