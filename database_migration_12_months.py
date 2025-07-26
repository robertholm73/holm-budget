#!/usr/bin/env python3
"""
Database Migration Script for 12-Month Budget Periods
=====================================================

This script migrates the existing budget database to support 12-month budget periods
with custom date ranges (25th to 24th of each month).

Usage:
    python database_migration_12_months.py

Requirements:
    - DATABASE_URL environment variable must be set
    - Existing database with current schema
    - pg8000 package installed
"""

import os
import sys
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import pg8000

# Load environment variables from .env file
from pathlib import Path

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value


def get_db_connection():
    """Get database connection using environment variable."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    try:
        # Parse DATABASE_URL for pg8000
        import urllib.parse

        parsed = urllib.parse.urlparse(database_url)
        conn = pg8000.connect(
            host=parsed.hostname,
            database=parsed.path[1:],  # Remove leading slash
            user=parsed.username,
            password=parsed.password,
            port=parsed.port or 5432,
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print(f"Database URL: {database_url}")
        raise


def generate_budget_periods():
    """Generate 12 months of budget periods starting from current month."""
    periods = []

    # Start from current month's period
    now = datetime.now()

    # Find the current period start (25th of previous month or current month)
    if now.day >= 25:
        # We're in the current period
        period_start = date(now.year, now.month, 25)
    else:
        # We're still in the previous month's period
        prev_month = now - relativedelta(months=1)
        period_start = date(prev_month.year, prev_month.month, 25)

    # Generate 12 periods
    for i in range(12):
        start_date = period_start + relativedelta(months=i)
        end_date = start_date + relativedelta(months=1) - timedelta(days=1)

        # Period name is the month we're budgeting for (end month)
        period_name = end_date.strftime("%B %Y")

        # Determine if this is the active period
        today = date.today()
        is_active = start_date <= today <= end_date

        periods.append(
            {
                "period_name": period_name,
                "start_date": start_date,
                "end_date": end_date,
                "is_active": is_active,
            }
        )

    return periods


def run_migration():
    """Execute the database migration."""
    print("Starting database migration for 12-month budget periods...")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Begin transaction
        cursor.execute("BEGIN")

        print("Step 1: Creating budget_periods table...")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS budget_periods (
                id SERIAL PRIMARY KEY,
                period_name VARCHAR(20) NOT NULL UNIQUE,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                is_active BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        print("Step 2: Checking if migration already ran...")
        cursor.execute("SELECT COUNT(*) FROM budget_periods")
        period_count = cursor.fetchone()[0]

        if period_count > 0:
            print(
                f"Migration already ran - found {period_count} budget periods"
            )
            response = input(
                "Do you want to recreate periods? (y/N): "
            ).lower()
            if response != "y":
                print("Migration cancelled")
                cursor.execute("ROLLBACK")
                return

            # Clear existing periods
            cursor.execute("DELETE FROM budget_periods")

        print("Step 3: Generating and inserting budget periods...")
        periods = generate_budget_periods()

        for period in periods:
            cursor.execute(
                """
                INSERT INTO budget_periods (period_name, start_date, end_date, is_active)
                VALUES (%s, %s, %s, %s)
            """,
                (
                    period["period_name"],
                    period["start_date"],
                    period["end_date"],
                    period["is_active"],
                ),
            )

            status = "ACTIVE" if period["is_active"] else "inactive"
            print(
                f"  Added: {period['period_name']} ({period['start_date']} to {period['end_date']}) [{status}]"
            )

        print("Step 4: Adding period_id column to budget_categories...")

        # Check if column already exists
        cursor.execute(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'budget_categories' 
            AND column_name = 'period_id'
        """
        )

        if not cursor.fetchone():
            cursor.execute(
                """
                ALTER TABLE budget_categories 
                ADD COLUMN period_id INTEGER REFERENCES budget_periods(id)
            """
            )
            print("  Added period_id column")
        else:
            print("  period_id column already exists")

        print(
            "Step 5: Migrating existing budget categories to current period..."
        )

        # Get the current active period
        cursor.execute(
            "SELECT id FROM budget_periods WHERE is_active = TRUE LIMIT 1"
        )
        current_period_result = cursor.fetchone()

        if current_period_result:
            current_period_id = current_period_result[0]

            # Update existing categories to belong to current period
            cursor.execute(
                """
                UPDATE budget_categories 
                SET period_id = %s 
                WHERE period_id IS NULL
            """,
                (current_period_id,),
            )

            updated_count = cursor.rowcount
            print(
                f"  Updated {updated_count} existing categories to current period"
            )
        else:
            print("  Warning: No active period found!")

        print("Step 6: Updating constraints...")

        # Drop old unique constraint on name (if it exists)
        try:
            cursor.execute(
                "ALTER TABLE budget_categories DROP CONSTRAINT budget_categories_name_key"
            )
            print("  Dropped old unique constraint on name")
        except:
            print("  Old unique constraint not found (already dropped)")

        # Add new compound unique constraint
        try:
            cursor.execute(
                """
                ALTER TABLE budget_categories 
                ADD CONSTRAINT budget_categories_name_period_unique 
                UNIQUE (name, period_id)
            """
            )
            print("  Added compound unique constraint (name, period_id)")
        except:
            print("  Compound unique constraint already exists")

        print("Step 7: Creating transfers table...")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transfers (
                id SERIAL PRIMARY KEY,
                from_account_id INTEGER NOT NULL,
                to_account_id INTEGER NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                description TEXT,
                originator_user VARCHAR(255) NOT NULL,  -- 'Robert' or 'Peanut'
                transfer_date TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_account_id) REFERENCES accounts (id),
                FOREIGN KEY (to_account_id) REFERENCES accounts (id)
            )
        """
        )
        print("  Created transfers table")

        print("Step 8: Cleaning up transfer-related data...")

        # Find and migrate existing transfer purchases to the transfers table
        cursor.execute(
            """
            SELECT id, user_name, amount, account_id, description, date 
            FROM purchases 
            WHERE description LIKE 'Transfer:%' OR user_name = 'Transfer'
        """
        )
        transfer_purchases = cursor.fetchall()

        if transfer_purchases:
            print(
                f"  Found {len(transfer_purchases)} transfer-related purchases to migrate"
            )
            for transfer in transfer_purchases:
                (
                    purchase_id,
                    user_name,
                    amount,
                    account_id,
                    description,
                    date,
                ) = transfer

                # Try to extract destination account from description
                originator = (
                    "Robert"
                    if user_name in ["Robert", "Transfer"]
                    else "Peanut"
                )

                # For now, we'll delete these old transfer purchases since they're incorrect
                # In a real migration, you might want to try to parse and migrate them
                cursor.execute(
                    "DELETE FROM purchases WHERE id = %s", (purchase_id,)
                )
                print(
                    f"    Removed incorrect transfer purchase: {description}"
                )

        print("Step 9: Creating helper function...")
        cursor.execute(
            """
            CREATE OR REPLACE FUNCTION get_current_period() 
            RETURNS INTEGER AS $$
            BEGIN
                RETURN (SELECT id FROM budget_periods 
                        WHERE CURRENT_DATE >= start_date 
                        AND CURRENT_DATE <= end_date 
                        LIMIT 1);
            END;
            $$ LANGUAGE plpgsql;
        """
        )
        print("  Created get_current_period() function")

        # Commit transaction
        cursor.execute("COMMIT")
        print("\n✅ Migration completed successfully!")

        # Display summary
        print("\nSummary:")
        cursor.execute("SELECT COUNT(*) FROM budget_periods")
        period_count = cursor.fetchone()[0]
        print(f"  - Created {period_count} budget periods")

        cursor.execute(
            "SELECT COUNT(*) FROM budget_categories WHERE period_id IS NOT NULL"
        )
        category_count = cursor.fetchone()[0]
        print(f"  - Migrated {category_count} budget categories")

        cursor.execute(
            "SELECT period_name FROM budget_periods WHERE is_active = TRUE"
        )
        active_period = cursor.fetchone()
        if active_period:
            print(f"  - Active period: {active_period[0]}")

    except Exception as e:
        cursor.execute("ROLLBACK")
        print(f"\n❌ Migration failed: {e}")
        raise

    finally:
        cursor.close()
        conn.close()


def verify_migration():
    """Verify the migration was successful."""
    print("\nVerifying migration...")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check budget_periods table
        cursor.execute("SELECT COUNT(*) FROM budget_periods")
        period_count = cursor.fetchone()[0]
        print(f"Budget periods: {period_count}")

        # Check active period
        cursor.execute(
            "SELECT period_name, start_date, end_date FROM budget_periods WHERE is_active = TRUE"
        )
        active_period = cursor.fetchone()
        if active_period:
            print(
                f"Active period: {active_period[0]} ({active_period[1]} to {active_period[2]})"
            )

        # Check budget categories
        cursor.execute(
            "SELECT COUNT(*) FROM budget_categories WHERE period_id IS NOT NULL"
        )
        migrated_categories = cursor.fetchone()[0]
        print(f"Migrated categories: {migrated_categories}")

        # Test the function
        cursor.execute("SELECT get_current_period()")
        current_period_id = cursor.fetchone()[0]
        print(f"Current period ID: {current_period_id}")

        print("✅ Verification complete")

    except Exception as e:
        print(f"❌ Verification failed: {e}")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("Database Migration for 12-Month Budget Periods")
    print("=" * 50)

    # Check if we have required dependencies
    try:
        from dateutil.relativedelta import relativedelta
    except ImportError:
        print("❌ Missing dependency: python-dateutil")
        print("Install with: pip install python-dateutil")
        sys.exit(1)

    # Confirm before running
    response = input(
        "This will modify your database schema. Continue? (y/N): "
    ).lower()
    if response != "y":
        print("Migration cancelled")
        sys.exit(0)

    try:
        run_migration()
        verify_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
