#!/usr/bin/env python3
"""
Database cleanup script for removing bad data
Run this once to clean up your database
"""
import os
import pg8000
import urllib.parse
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


def cleanup_database():
    """Clean up bad data and add constraints"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        print("🧹 Starting database cleanup...")

        # 1. Clean up bad accounts
        print("Removing accounts with generic names and zero balance...")
        cur.execute(
            """
            DELETE FROM accounts 
            WHERE (name LIKE 'Bank Account %' OR name LIKE 'Account %' OR name = '' OR name IS NULL) 
            AND balance = 0
        """
        )
        deleted_accounts = cur.rowcount
        print(f"✅ Deleted {deleted_accounts} bad accounts")

        # 2. Clean up unwanted default budget categories
        print("Removing unwanted default budget categories...")
        unwanted_categories = [
            "Food",
            "Transport",
            "Shopping",
            "Bills",
            "Entertainment",
            "Health",
            "Other",
        ]
        placeholders = ", ".join(["%s"] * len(unwanted_categories))
        cur.execute(
            f"""
            DELETE FROM budget_categories 
            WHERE name IN ({placeholders})
            AND NOT (name LIKE 'Peanut -%' OR name LIKE 'Robert -%')
        """,
            unwanted_categories,
        )
        deleted_unwanted = cur.rowcount
        print(f"✅ Deleted {deleted_unwanted} unwanted default categories")

        # 3. Clean up empty budget categories
        print("Removing empty budget categories...")
        cur.execute(
            """
            DELETE FROM budget_categories 
            WHERE (name = '' OR name IS NULL) 
            AND budgeted_amount = 0 
            AND current_balance = 0
        """
        )
        deleted_empty = cur.rowcount
        print(f"✅ Deleted {deleted_empty} empty categories")

        # 4. Clean up orphaned purchases (optional - be careful!)
        print("Checking for orphaned purchases...")
        cur.execute(
            """
            SELECT COUNT(*) FROM purchases 
            WHERE account_id IS NOT NULL 
            AND account_id NOT IN (SELECT id FROM accounts)
        """
        )
        orphaned_purchases = cur.fetchone()[0]
        if orphaned_purchases > 0:
            response = input(
                f"Found {orphaned_purchases} orphaned purchases. Delete them? (y/N): "
            )
            if response.lower() == "y":
                cur.execute(
                    """
                    DELETE FROM purchases 
                    WHERE account_id IS NOT NULL 
                    AND account_id NOT IN (SELECT id FROM accounts)
                """
                )
                print(f"✅ Deleted {orphaned_purchases} orphaned purchases")

        # 5. Add constraints to prevent future issues
        print("Adding database constraints...")

        # Check if constraints already exist
        cur.execute(
            """
            SELECT constraint_name FROM information_schema.table_constraints 
            WHERE table_name = 'accounts' AND constraint_name = 'accounts_name_not_empty'
        """
        )
        if not cur.fetchone():
            try:
                cur.execute(
                    """
                    ALTER TABLE accounts 
                    ADD CONSTRAINT accounts_name_not_empty 
                    CHECK (name IS NOT NULL AND LENGTH(TRIM(name)) > 0)
                """
                )
                print("✅ Added constraint for account names")
            except Exception as e:
                print(f"⚠️ Could not add account constraint: {e}")

        cur.execute(
            """
            SELECT constraint_name FROM information_schema.table_constraints 
            WHERE table_name = 'budget_categories' AND constraint_name = 'categories_name_not_empty'
        """
        )
        if not cur.fetchone():
            try:
                cur.execute(
                    """
                    ALTER TABLE budget_categories 
                    ADD CONSTRAINT categories_name_not_empty 
                    CHECK (name IS NOT NULL AND LENGTH(TRIM(name)) > 0)
                """
                )
                print("✅ Added constraint for category names")
            except Exception as e:
                print(f"⚠️ Could not add category constraint: {e}")

        # 6. Show current state
        print("\n📊 Current database state:")
        cur.execute("SELECT COUNT(*) FROM accounts")
        account_count = cur.fetchone()[0]
        print(f"   Accounts: {account_count}")

        cur.execute("SELECT COUNT(*) FROM budget_categories")
        category_count = cur.fetchone()[0]
        print(f"   Budget Categories: {category_count}")

        cur.execute("SELECT COUNT(*) FROM purchases")
        purchase_count = cur.fetchone()[0]
        print(f"   Purchases: {purchase_count}")

        # Commit all changes
        conn.commit()
        conn.close()

        print(f"\n🎉 Cleanup completed successfully!")
        print(f"   Removed {deleted_accounts} bad accounts")
        print(f"   Removed {deleted_unwanted} unwanted default categories")
        print(f"   Removed {deleted_empty} empty categories")
        print("   Added validation constraints")

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        if "conn" in locals():
            conn.rollback()
            conn.close()


def show_accounts():
    """Show all current accounts"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id, name, balance FROM accounts ORDER BY name")
        accounts = cur.fetchall()

        print("\n📋 Current Accounts:")
        print("ID  | Name                    | Balance")
        print("----|-------------------------|----------")
        for acc in accounts:
            print(f"{acc[0]:<3} | {acc[1]:<23} | R{acc[2]:.2f}")

        conn.close()

    except Exception as e:
        print(f"❌ Error showing accounts: {e}")


if __name__ == "__main__":
    print("💰 Budget Database Cleanup Tool")
    print("=" * 40)

    while True:
        print("\nOptions:")
        print("1. Show current accounts")
        print("2. Run cleanup")
        print("3. Exit")

        choice = input("\nSelect option (1-3): ").strip()

        if choice == "1":
            show_accounts()
        elif choice == "2":
            cleanup_database()
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")
