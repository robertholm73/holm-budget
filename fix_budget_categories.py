#!/usr/bin/env python3
"""
Fix Budget Categories Database Issues
=====================================

This script identifies and fixes duplicate budget category issues.
"""

import os
import pg8000
import urllib.parse
import json

# Load .env file
env_file = '.env'
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

def get_db_connection():
    """Get database connection using environment variable."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    parsed = urllib.parse.urlparse(database_url)
    return pg8000.connect(
        host=parsed.hostname,
        database=parsed.path[1:],
        user=parsed.username,
        password=parsed.password,
        port=parsed.port or 5432,
        ssl_context=True
    )

def load_settings():
    """Load settings from config file."""
    try:
        with open('config/settings.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: config/settings.json not found")
        return {}

def check_database_state():
    """Check current database state for budget categories."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("=== CHECKING DATABASE STATE ===\n")
    
    # Check if budget_periods table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'budget_periods'
        )
    """)
    has_periods = cur.fetchone()[0]
    print(f"Has budget_periods table: {has_periods}")
    
    # Check budget_categories table structure
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'budget_categories'
        ORDER BY ordinal_position
    """)
    columns = cur.fetchall()
    print(f"\nBudget categories table structure:")
    for col in columns:
        print(f"  {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
    
    # Check unique constraints
    cur.execute("""
        SELECT tc.constraint_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = 'budget_categories'
        AND tc.constraint_type = 'UNIQUE'
    """)
    constraints = cur.fetchall()
    print(f"\nUnique constraints:")
    for constraint in constraints:
        print(f"  {constraint[0]}: {constraint[1]}")
    
    # Check all budget categories
    cur.execute("SELECT id, name, budgeted_amount, current_balance FROM budget_categories ORDER BY name")
    categories = cur.fetchall()
    print(f"\nAll budget categories ({len(categories)} total):")
    for cat in categories:
        print(f"  ID {cat[0]}: {cat[1]} (budgeted: {cat[2]}, current: {cat[3]})")
    
    # Check for duplicates
    cur.execute("""
        SELECT name, COUNT(*) as count
        FROM budget_categories
        GROUP BY name
        HAVING COUNT(*) > 1
    """)
    duplicates = cur.fetchall()
    if duplicates:
        print(f"\nDUPLICATE CATEGORIES FOUND:")
        for dup in duplicates:
            print(f"  {dup[0]}: {dup[1]} copies")
    else:
        print(f"\nNo duplicate categories found.")
    
    conn.close()
    return has_periods, duplicates

def fix_duplicates():
    """Fix duplicate budget categories."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("\n=== FIXING DUPLICATES ===\n")
    
    # Get duplicates with full details
    cur.execute("""
        SELECT id, name, budgeted_amount, current_balance
        FROM budget_categories
        WHERE name IN (
            SELECT name
            FROM budget_categories
            GROUP BY name
            HAVING COUNT(*) > 1
        )
        ORDER BY name, id
    """)
    
    duplicates = cur.fetchall()
    if not duplicates:
        print("No duplicates to fix.")
        conn.close()
        return
    
    # Group by name
    categories_by_name = {}
    for dup in duplicates:
        name = dup[1]
        if name not in categories_by_name:
            categories_by_name[name] = []
        categories_by_name[name].append(dup)
    
    # Fix each duplicate group
    for name, category_group in categories_by_name.items():
        print(f"Fixing duplicates for: {name}")
        
        # Keep the first one (lowest ID), merge data from others
        keep_category = category_group[0]
        keep_id = keep_category[0]
        
        # Calculate merged amounts
        total_budgeted = sum(cat[2] for cat in category_group)
        total_current = sum(cat[3] for cat in category_group)
        
        print(f"  Keeping ID {keep_id}, merging {len(category_group)} duplicates")
        print(f"  Total budgeted: {total_budgeted}, Total current: {total_current}")
        
        # Update the category we're keeping
        cur.execute("""
            UPDATE budget_categories 
            SET budgeted_amount = %s, current_balance = %s
            WHERE id = %s
        """, (total_budgeted, total_current, keep_id))
        
        # Update any purchases that reference the duplicates
        duplicate_ids = [cat[0] for cat in category_group[1:]]
        for dup_id in duplicate_ids:
            cur.execute("""
                UPDATE purchases 
                SET budget_category_id = %s
                WHERE budget_category_id = %s
            """, (keep_id, dup_id))
            
            # Delete the duplicate
            cur.execute("DELETE FROM budget_categories WHERE id = %s", (dup_id,))
            print(f"  Deleted duplicate ID {dup_id}")
    
    conn.commit()
    conn.close()
    print("Duplicates fixed successfully!")

def ensure_config_categories():
    """Ensure all categories from config exist in database."""
    settings = load_settings()
    if not settings:
        return
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("\n=== ENSURING CONFIG CATEGORIES ===\n")
    
    budget_categories = settings.get("budget_categories", {})
    for user, categories in budget_categories.items():
        for category, amount in categories.items():
            category_name = f"{user} - {category}"
            
            # Check if category exists
            cur.execute("SELECT id FROM budget_categories WHERE name = %s", (category_name,))
            if not cur.fetchone():
                # Create missing category
                cur.execute("""
                    INSERT INTO budget_categories (name, budgeted_amount, current_balance)
                    VALUES (%s, %s, %s)
                """, (category_name, float(amount), float(amount)))
                print(f"Created missing category: {category_name}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    try:
        has_periods, duplicates = check_database_state()
        
        if duplicates:
            fix_duplicates()
            print("\n" + "="*50)
            print("AFTER FIXING - CHECKING STATE AGAIN")
            check_database_state()
        
        ensure_config_categories()
        
        print("\n=== FINAL STATE ===")
        check_database_state()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()