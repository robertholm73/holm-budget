#!/usr/bin/env python3
"""
Direct SQLite budget population script for August 2025
"""

import sqlite3
import json
from datetime import datetime

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

def populate_august_budget():
    """Populate August 2025 budget with values from settings.json"""
    try:
        settings = load_settings()
        if not settings:
            return False
        
        # Connect to local SQLite database
        conn = sqlite3.connect('budget.db')
        cur = conn.cursor()
        
        print("Starting August 2025 budget population...")
        print("=" * 50)
        
        # 1. Populate budget categories
        budget_categories = settings.get("budget_categories", {})
        categories_created = 0
        categories_updated = 0
        
        for user, categories in budget_categories.items():
            print(f"\nProcessing {user}'s categories:")
            
            for category, amount in categories.items():
                if isinstance(amount, dict):
                    # Handle nested categories like Town Council
                    for sub_category, sub_amount in amount.items():
                        category_name = f"{user} - {category} - {sub_category}"
                        
                        # Check if category exists
                        cur.execute('SELECT id FROM budget_categories WHERE name = ?', (category_name,))
                        existing = cur.fetchone()
                        
                        if existing:
                            # Update existing category
                            cur.execute('''
                                UPDATE budget_categories 
                                SET budgeted_amount = ?, current_balance = ?
                                WHERE name = ?
                            ''', (float(sub_amount), float(sub_amount), category_name))
                            categories_updated += 1
                            print(f"  ✓ Updated: {category_name} = R{sub_amount}")
                        else:
                            # Create new category
                            cur.execute('''
                                INSERT INTO budget_categories (name, budgeted_amount, current_balance)
                                VALUES (?, ?, ?)
                            ''', (category_name, float(sub_amount), float(sub_amount)))
                            categories_created += 1
                            print(f"  + Created: {category_name} = R{sub_amount}")
                else:
                    category_name = f"{user} - {category}"
                    
                    # Check if category exists
                    cur.execute('SELECT id FROM budget_categories WHERE name = ?', (category_name,))
                    existing = cur.fetchone()
                    
                    if existing:
                        # Update existing category
                        cur.execute('''
                            UPDATE budget_categories 
                            SET budgeted_amount = ?, current_balance = ?
                            WHERE name = ?
                        ''', (float(amount), float(amount), category_name))
                        categories_updated += 1
                        print(f"  ✓ Updated: {category_name} = R{amount}")
                    else:
                        # Create new category
                        cur.execute('''
                            INSERT INTO budget_categories (name, budgeted_amount, current_balance)
                            VALUES (?, ?, ?)
                        ''', (category_name, float(amount), float(amount)))
                        categories_created += 1
                        print(f"  + Created: {category_name} = R{amount}")
        
        # 2. Add Robert's salary
        income_data = settings.get("Income", {})
        robert_salary = income_data.get("Robert", 0)
        
        if robert_salary > 0:
            print(f"\nProcessing salary...")
            
            # Find Robert's Bank Zero Cheque account
            cur.execute('SELECT id, balance FROM accounts WHERE name = ?', ("Robert - Bank Zero Cheque",))
            result = cur.fetchone()
            
            if result:
                account_id, current_balance = result
                
                # Add salary to account
                cur.execute('''
                    UPDATE accounts 
                    SET balance = balance + ? 
                    WHERE id = ?
                ''', (robert_salary, account_id))
                
                # Record salary transaction
                cur.execute('''
                    INSERT INTO purchases (user_name, amount, account_id, budget_category_id, description, date)
                    VALUES (?, ?, ?, NULL, ?, ?)
                ''', ("Robert", -robert_salary, account_id, "Monthly salary - August 2025", datetime.now().isoformat()))
                
                new_balance = current_balance + robert_salary
                print(f"  ✓ Added R{robert_salary} salary to Robert - Bank Zero Cheque")
                print(f"    Account balance: R{current_balance} → R{new_balance}")
            else:
                print("  ⚠ Warning: Robert - Bank Zero Cheque account not found")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 50)
        print("✅ August 2025 budget population completed!")
        print(f"   • {categories_created} categories created")
        print(f"   • {categories_updated} categories updated")
        print(f"   • R{robert_salary} salary added")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = populate_august_budget()
    if not success:
        print("\n❌ Budget population failed!")
        exit(1)