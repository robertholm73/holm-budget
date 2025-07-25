#!/usr/bin/env python3
"""
Fix Period Assignments for Budget Categories
===========================================

This script assigns NULL period_id categories to the current active period.
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

def check_periods_and_assignments():
    """Check current periods and category assignments."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("=== CHECKING BUDGET PERIODS ===\n")
    
    # Check budget periods
    cur.execute('''
        SELECT id, period_name, start_date, end_date, is_active
        FROM budget_periods
        ORDER BY start_date
    ''')
    periods = cur.fetchall()
    
    print(f"Budget periods ({len(periods)} total):")
    active_period_id = None
    for period in periods:
        active_status = "ACTIVE" if period[4] else "inactive"
        print(f"  ID {period[0]}: {period[1]} ({period[2]} to {period[3]}) - {active_status}")
        if period[4]:
            active_period_id = period[0]
    
    print(f"\nActive period ID: {active_period_id}")
    
    # Check categories without period_id
    cur.execute('''
        SELECT id, name, budgeted_amount, period_id
        FROM budget_categories
        WHERE period_id IS NULL
        ORDER BY name
    ''')
    null_categories = cur.fetchall()
    
    print(f"\nCategories with NULL period_id ({len(null_categories)} total):")
    for cat in null_categories:
        print(f"  ID {cat[0]}: {cat[1]} (budgeted: {cat[2]})")
    
    # Check categories with period_id
    cur.execute('''
        SELECT COUNT(*), period_id
        FROM budget_categories
        WHERE period_id IS NOT NULL
        GROUP BY period_id
        ORDER BY period_id
    ''')
    period_counts = cur.fetchall()
    
    print(f"\nCategories by period:")
    for count, period_id in period_counts:
        print(f"  Period {period_id}: {count} categories")
    
    conn.close()
    return active_period_id, null_categories

def fix_period_assignments(active_period_id):
    """Assign NULL period_id categories to active period."""
    if not active_period_id:
        print("No active period found! Cannot assign categories.")
        return
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    print(f"\n=== FIXING PERIOD ASSIGNMENTS ===\n")
    
    # Update all categories with NULL period_id to active period
    cur.execute('''
        UPDATE budget_categories
        SET period_id = %s
        WHERE period_id IS NULL
    ''', (active_period_id,))
    
    updated_count = cur.rowcount
    print(f"Updated {updated_count} categories to period {active_period_id}")
    
    conn.commit()
    conn.close()
    
    return updated_count

if __name__ == "__main__":
    try:
        active_period_id, null_categories = check_periods_and_assignments()
        
        if null_categories:
            print("\nFound categories with NULL period_id. Fixing...")
            updated_count = fix_period_assignments(active_period_id)
            
            if updated_count > 0:
                print(f"\n=== VERIFICATION ===")
                check_periods_and_assignments()
        else:
            print("\nNo categories with NULL period_id found. All good!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()