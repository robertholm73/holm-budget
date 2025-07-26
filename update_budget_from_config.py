#!/usr/bin/env python3
"""
Update Budget Categories from Config
===================================

This script updates existing budget categories with amounts from settings.json.
"""

import os
import pg8000
import urllib.parse
import json

# Load .env file
env_file = ".env"
if os.path.exists(env_file):
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
    """Load settings from config file."""
    try:
        with open("config/settings.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: config/settings.json not found")
        return {}


def update_budget_categories():
    """Update budget categories with amounts from settings.json."""
    settings = load_settings()
    if not settings:
        return

    conn = get_db_connection()
    cur = conn.cursor()

    print("=== UPDATING BUDGET CATEGORIES FROM CONFIG ===\n")

    budget_categories = settings.get("budget_categories", {})
    categories_updated = 0

    for user, categories in budget_categories.items():
        for category, amount in categories.items():
            category_name = f"{user} - {category}"

            # Check if category exists
            cur.execute(
                "SELECT id, budgeted_amount FROM budget_categories WHERE name = %s",
                (category_name,),
            )
            result = cur.fetchone()

            if result:
                current_id, current_amount = result
                new_amount = float(amount)

                if float(current_amount) != new_amount:
                    # Update budgeted amount
                    cur.execute(
                        """
                        UPDATE budget_categories 
                        SET budgeted_amount = %s
                        WHERE id = %s
                    """,
                        (new_amount, current_id),
                    )

                    print(
                        f"Updated {category_name}: {current_amount} -> {new_amount}"
                    )
                    categories_updated += 1
                else:
                    print(
                        f"No change needed for {category_name}: {current_amount}"
                    )
            else:
                # Create missing category
                cur.execute(
                    """
                    INSERT INTO budget_categories (name, budgeted_amount, current_balance)
                    VALUES (%s, %s, 0)
                """,
                    (category_name, float(amount)),
                )
                print(
                    f"Created missing category: {category_name} with amount {amount}"
                )
                categories_updated += 1

    conn.commit()
    conn.close()

    print(f"\nUpdate completed! {categories_updated} categories updated.")


if __name__ == "__main__":
    try:
        update_budget_categories()
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
