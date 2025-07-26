#!/usr/bin/env python3
"""
Final fix for August 2025 budget population
This script properly removes all name-only constraints and populates August budget
"""

import os
import pg8000
import urllib.parse
import json
from datetime import datetime
from pathlib import Path
from decimal import Decimal


def load_env():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value


def load_settings():
    """Load settings from config file"""
    try:
        with open("config/settings.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: config/settings.json not found")
        return None
    except json.JSONDecodeError:
        print("Error: config/settings.json is not valid JSON")
        return None


def get_db_connection():
    """Get database connection using environment variable"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    parsed = urllib.parse.urlparse(database_url)
    print(f"Connecting to database: {parsed.hostname}")

    return pg8000.connect(
        host=parsed.hostname,
        database=parsed.path[1:],
        user=parsed.username,
        password=parsed.password,
        port=parsed.port or 5432,
        ssl_context=True,
        timeout=30,
    )


def fix_all_constraints(conn):
    """Remove ALL name-only unique constraints and add the correct one"""
    cur = conn.cursor()

    print("Fixing all constraints on budget_categories...")

    # Get ALL constraints on budget_categories table
    cur.execute(
        """
        SELECT constraint_name, constraint_type 
        FROM information_schema.table_constraints 
        WHERE table_name = 'budget_categories' 
        AND constraint_type = 'UNIQUE'
    """
    )
    constraints = cur.fetchall()

    print(f"Found {len(constraints)} unique constraints:")
    for constraint in constraints:
        print(f"  • {constraint[0]} ({constraint[1]})")

    # Drop all unique constraints (we'll recreate the correct one)
    for constraint in constraints:
        constraint_name = constraint[0]
        try:
            print(f"Dropping constraint: {constraint_name}")
            cur.execute(
                f"ALTER TABLE budget_categories DROP CONSTRAINT {constraint_name}"
            )
            print(f"  ✓ Dropped {constraint_name}")
        except Exception as e:
            print(f"  ⚠ Could not drop {constraint_name}: {e}")

    # Add the correct unique constraint
    try:
        print("Adding correct unique constraint (name, period_id)...")
        cur.execute(
            """
            ALTER TABLE budget_categories 
            ADD CONSTRAINT budget_categories_name_period_unique 
            UNIQUE (name, period_id)
        """
        )
        print("✓ Added unique constraint on (name, period_id)")
    except Exception as e:
        print(f"⚠ Could not add constraint: {e}")

    conn.commit()
    print("✓ Constraint fixes completed")


def switch_to_august_period(conn):
    """Switch active period to August 2025"""
    cur = conn.cursor()

    print("Switching active period to August 2025...")

    try:
        # First, make all periods inactive
        cur.execute("UPDATE budget_periods SET is_active = FALSE")

        # Then make August 2025 active
        cur.execute(
            "UPDATE budget_periods SET is_active = TRUE WHERE period_name = %s",
            ("August 2025",),
        )

        # Check if August period exists and get its ID
        cur.execute(
            "SELECT id FROM budget_periods WHERE period_name = %s",
            ("August 2025",),
        )
        result = cur.fetchone()

        if result:
            period_id = result[0]
            print(f"✓ August 2025 period is now active (ID: {period_id})")
            conn.commit()
            return period_id
        else:
            print("❌ August 2025 period not found!")
            return None

    except Exception as e:
        print(f"❌ Error switching period: {e}")
        conn.rollback()
        return None


def clear_august_categories(conn, period_id):
    """Clear existing budget categories for August period"""
    cur = conn.cursor()

    print(
        f"Clearing existing August 2025 budget categories (period {period_id})..."
    )

    try:
        # Get count before deletion
        cur.execute(
            "SELECT COUNT(*) FROM budget_categories WHERE period_id = %s",
            (period_id,),
        )
        count_before = cur.fetchone()[0]

        if count_before > 0:
            # Clear purchases that reference these categories first
            cur.execute(
                """
                UPDATE purchases 
                SET budget_category_id = NULL 
                WHERE budget_category_id IN (
                    SELECT id FROM budget_categories WHERE period_id = %s
                )
            """,
                (period_id,),
            )

            # Delete the categories
            cur.execute(
                "DELETE FROM budget_categories WHERE period_id = %s",
                (period_id,),
            )
            print(f"✓ Cleared {count_before} existing August categories")
        else:
            print("✓ No existing August categories to clear")

        conn.commit()

    except Exception as e:
        print(f"❌ Error clearing categories: {e}")
        conn.rollback()


def populate_budget_categories(conn, settings, period_id):
    """Populate budget categories for August 2025"""
    cur = conn.cursor()

    print(
        f"\nPopulating budget categories for August 2025 (period {period_id})..."
    )

    budget_categories = settings.get("budget_categories", {})
    if not budget_categories:
        print("No budget categories found in settings")
        return 0

    categories_created = 0

    for user, categories in budget_categories.items():
        print(f"\nProcessing {user}'s categories:")

        for category, amount in categories.items():
            if isinstance(amount, dict):
                # Handle nested categories like Town Council
                for sub_category, sub_amount in amount.items():
                    category_name = f"{user} - {category} - {sub_category}"

                    try:
                        cur.execute(
                            """
                            INSERT INTO budget_categories (name, budgeted_amount, current_balance, period_id)
                            VALUES (%s, %s, %s, %s)
                        """,
                            (
                                category_name,
                                float(sub_amount),
                                float(sub_amount),
                                period_id,
                            ),
                        )
                        categories_created += 1
                        print(f"  ✓ Created: {category_name} = R{sub_amount}")
                    except Exception as e:
                        print(f"  ❌ Failed to create {category_name}: {e}")
            else:
                category_name = f"{user} - {category}"

                try:
                    cur.execute(
                        """
                        INSERT INTO budget_categories (name, budgeted_amount, current_balance, period_id)
                        VALUES (%s, %s, %s, %s)
                    """,
                        (
                            category_name,
                            float(amount),
                            float(amount),
                            period_id,
                        ),
                    )
                    categories_created += 1
                    print(f"  ✓ Created: {category_name} = R{amount}")
                except Exception as e:
                    print(f"  ❌ Failed to create {category_name}: {e}")

    try:
        conn.commit()
        print(f"\n✓ Successfully created {categories_created} categories")
    except Exception as e:
        print(f"❌ Error committing categories: {e}")
        conn.rollback()
        return 0

    return categories_created


def add_monthly_income(conn, settings):
    """Add monthly income to accounts"""
    cur = conn.cursor()

    print("\nProcessing monthly income...")

    income_data = settings.get("Income", {})
    if not income_data:
        print("No income data found in settings")
        return 0

    total_income_added = 0

    for user, salary in income_data.items():
        if salary > 0:
            # Find user's primary account
            account_patterns = [
                f"{user} - Bank Zero Cheque",
                f"{user} - Cheque",
                f"{user} - Primary",
                f"{user} - Main",
            ]

            account_found = False
            for pattern in account_patterns:
                try:
                    cur.execute(
                        "SELECT id, balance, name FROM accounts WHERE name = %s",
                        (pattern,),
                    )
                    result = cur.fetchone()
                    if result:
                        account_id, current_balance, account_name = result

                        # Convert current_balance to float if it's Decimal
                        if isinstance(current_balance, Decimal):
                            current_balance = float(current_balance)

                        try:
                            # Add salary to account
                            cur.execute(
                                "UPDATE accounts SET balance = balance + %s WHERE id = %s",
                                (float(salary), account_id),
                            )

                            # Record salary transaction (negative amount = income)
                            cur.execute(
                                """
                                INSERT INTO purchases (user_name, amount, account_id, budget_category_id, description, date)
                                VALUES (%s, %s, %s, NULL, %s, %s)
                            """,
                                (
                                    user,
                                    -float(salary),
                                    account_id,
                                    f"Monthly salary - August 2025",
                                    datetime.now(),
                                ),
                            )

                            conn.commit()

                            new_balance = current_balance + float(salary)
                            total_income_added += float(salary)
                            print(
                                f"  ✓ Added R{salary} salary to {account_name}"
                            )
                            print(
                                f"    Account balance: R{current_balance:.2f} → R{new_balance:.2f}"
                            )
                            account_found = True
                            break

                        except Exception as e:
                            print(f"  ❌ Failed to add salary for {user}: {e}")
                            conn.rollback()

                except Exception as e:
                    print(f"  ⚠ Error checking account {pattern}: {e}")
                    conn.rollback()

            if not account_found:
                print(
                    f"  ⚠ Warning: No suitable account found for {user}'s salary"
                )
                print(f"    Looked for: {', '.join(account_patterns)}")

    return total_income_added


def show_summary(conn, period_id):
    """Show summary of what was created"""
    cur = conn.cursor()

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    try:
        # Show active period
        cur.execute(
            "SELECT period_name FROM budget_periods WHERE is_active = TRUE"
        )
        active_period = cur.fetchone()
        if active_period:
            print(f"Active period: {active_period[0]}")

        # Show budget categories count for August
        cur.execute(
            "SELECT COUNT(*) FROM budget_categories WHERE period_id = %s",
            (period_id,),
        )
        category_count = cur.fetchone()[0]
        print(f"August budget categories: {category_count}")

        # Show total budgeted amount for August
        cur.execute(
            "SELECT SUM(budgeted_amount) FROM budget_categories WHERE period_id = %s",
            (period_id,),
        )
        total_budgeted = cur.fetchone()[0] or 0
        print(f"Total August budget: R{float(total_budgeted):.2f}")

        # Show account balances
        cur.execute("SELECT COUNT(*), SUM(balance) FROM accounts")
        account_data = cur.fetchone()
        account_count, total_balance = account_data[0], account_data[1] or 0
        print(
            f"Accounts: {account_count} (Total balance: R{float(total_balance):.2f})"
        )

        # Show some sample categories
        if category_count > 0:
            cur.execute(
                """
                SELECT name, budgeted_amount 
                FROM budget_categories 
                WHERE period_id = %s 
                ORDER BY budgeted_amount DESC 
                LIMIT 5
            """,
                (period_id,),
            )
            top_categories = cur.fetchall()

            if top_categories:
                print(f"\nTop 5 budget categories:")
                for cat in top_categories:
                    print(f"  • {cat[0]}: R{float(cat[1]):.2f}")

    except Exception as e:
        print(f"Error generating summary: {e}")


def main():
    """Main function to fix constraints and populate August 2025 budget"""
    print("Final Fix & Populate August 2025 Budget")
    print("=" * 45)

    # Load environment and settings
    load_env()
    settings = load_settings()
    if not settings:
        return False

    try:
        # Connect to database
        conn = get_db_connection()
        print("✓ Connected to database successfully")

        # Fix ALL constraints properly
        fix_all_constraints(conn)

        # Switch to August period
        period_id = switch_to_august_period(conn)
        if not period_id:
            print("❌ Could not switch to August 2025 period")
            return False

        # Ask user if they want to clear existing categories
        response = (
            input(
                "\nDo you want to clear existing August categories and start fresh? (y/N): "
            )
            .strip()
            .lower()
        )
        if response in ["y", "yes"]:
            clear_august_categories(conn, period_id)

        # Populate budget categories
        categories_created = populate_budget_categories(
            conn, settings, period_id
        )

        # Add monthly income
        income_added = add_monthly_income(conn, settings)

        # Show summary
        show_summary(conn, period_id)

        print(f"\n✅ August 2025 budget population completed!")
        print(f"   • {categories_created} budget categories created")
        print(f"   • R{income_added:.2f} monthly income added")
        print(f"\n🎉 Your desktop app should now work with August 2025 data!")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Budget population failed!")
        exit(1)
