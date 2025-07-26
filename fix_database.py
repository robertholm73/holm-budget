#!/usr/bin/env python3
"""
Script to fix the database issues:
1. Remove hardcoded "Bank Account X" entries
2. Update "Bank 0" to "Bank Zero"
3. Ensure only accounts from config/settings.json exist
"""
import os
import pg8000
import urllib.parse
import json
from pathlib import Path

# Load environment variables from .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value


def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    parsed = urllib.parse.urlparse(database_url)
    return pg8000.connect(
        host=parsed.hostname,
        database=parsed.path[1:],
        user=parsed.username,
        password=parsed.password,
        port=parsed.port or 5432,
        ssl_context=True,
    )


def load_settings():
    try:
        with open("config/settings.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: config/settings.json not found")
        return None


def fix_database():
    """Fix all database issues"""
    try:
        settings = load_settings()
        if not settings:
            return

        conn = get_db_connection()
        cur = conn.cursor()

        print("🔧 Starting database cleanup and migration...")

        # 1. Remove hardcoded "Bank Account X" entries
        print("Removing hardcoded 'Bank Account X' entries...")
        cur.execute(
            """
            DELETE FROM accounts 
            WHERE name LIKE 'Bank Account %' AND name ~ '^Bank Account [0-9]+$'
        """
        )
        deleted_accounts = cur.rowcount
        print(f"✅ Removed {deleted_accounts} hardcoded bank accounts")

        # 2. Update "Bank 0" to "Bank Zero" in account names
        print("Updating 'Bank 0' to 'Bank Zero' in account names...")
        cur.execute(
            """
            UPDATE accounts 
            SET name = REPLACE(name, 'Bank 0', 'Bank Zero')
            WHERE name LIKE '%Bank 0%' AND name NOT LIKE '%Bank Zero%'
        """
        )
        updated_accounts = cur.rowcount
        print(
            f"✅ Updated {updated_accounts} account names from 'Bank 0' to 'Bank Zero'"
        )

        # 3. Ensure all accounts from config exist
        print("Ensuring all accounts from config exist...")
        accounts_added = 0
        for user, accounts in settings.get("bank_accounts", {}).items():
            for account_type in accounts:
                account_name = f"{user} - {account_type}"
                cur.execute(
                    """
                    INSERT INTO accounts (name, account_type, balance) 
                    VALUES (%s, %s, 0) ON CONFLICT (name) DO NOTHING
                """,
                    (account_name, "bank"),
                )
                if cur.rowcount > 0:
                    accounts_added += 1
        print(f"✅ Added {accounts_added} new accounts from config")

        # 4. Ensure all budget categories from config exist
        print("Ensuring all budget categories from config exist...")
        categories_added = 0
        for user, categories in settings.get("budget_categories", {}).items():
            for category in categories:
                category_name = f"{user} - {category}"
                cur.execute(
                    """
                    INSERT INTO budget_categories (name, budgeted_amount, current_balance) 
                    VALUES (%s, 0, 0) ON CONFLICT (name) DO NOTHING
                """,
                    (category_name,),
                )
                if cur.rowcount > 0:
                    categories_added += 1
        print(f"✅ Added {categories_added} new budget categories from config")

        # 5. Show final state
        print("\n📊 Final database state:")
        cur.execute("SELECT COUNT(*) FROM accounts")
        account_count = cur.fetchone()[0]
        print(f"   Total Accounts: {account_count}")

        cur.execute("SELECT COUNT(*) FROM budget_categories")
        category_count = cur.fetchone()[0]
        print(f"   Total Budget Categories: {category_count}")

        # Show all accounts
        print("\n📋 All accounts:")
        cur.execute("SELECT id, name, balance FROM accounts ORDER BY name")
        accounts = cur.fetchall()
        for acc in accounts:
            print(f"   {acc[0]}: {acc[1]} (R{acc[2]:.2f})")

        conn.commit()
        conn.close()

        print(f"\n🎉 Database cleanup completed successfully!")
        print(f"   Removed {deleted_accounts} hardcoded accounts")
        print(f"   Updated {updated_accounts} account names")
        print(f"   Added {accounts_added} accounts from config")
        print(f"   Added {categories_added} categories from config")

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        if "conn" in locals():
            conn.rollback()
            conn.close()


if __name__ == "__main__":
    print("🔧 Database Fix Script")
    print("=" * 40)

    response = input(
        "This will clean up hardcoded accounts and fix Bank 0 -> Bank Zero. Continue? (y/N): "
    )
    if response.lower() == "y":
        fix_database()
    else:
        print("Operation cancelled.")
