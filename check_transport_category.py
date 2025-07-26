#!/usr/bin/env python3
"""
Check Robert - Transport Category
================================

Check the specific details of Robert - Transport category.
"""

import os
import pg8000
import urllib.parse

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


def check_transport_category():
    """Check Robert - Transport category details."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Check Robert - Transport specifically
    cur.execute(
        """
        SELECT id, name, budgeted_amount, current_balance, period_id
        FROM budget_categories
        WHERE name = 'Robert - Transport'
    """
    )

    result = cur.fetchone()
    if result:
        print(f"Robert - Transport category found:")
        print(f"  ID: {result[0]}")
        print(f"  Name: {result[1]}")
        print(f"  Budgeted Amount: {result[2]}")
        print(f"  Current Balance: {result[3]}")
        print(f"  Period ID: {result[4]}")

        # Check if this period is active
        if result[4]:
            cur.execute(
                """
                SELECT period_name, is_active
                FROM budget_periods
                WHERE id = %s
            """,
                (result[4],),
            )
            period_info = cur.fetchone()
            if period_info:
                active_status = "ACTIVE" if period_info[1] else "inactive"
                print(f"  Period: {period_info[0]} ({active_status})")
    else:
        print("Robert - Transport category not found!")

    # Check what the desktop app query would return
    print(f"\n=== Desktop App Query Simulation ===")
    cur.execute(
        """
        SELECT bc.id, bc.name, bc.budgeted_amount, bc.current_balance 
        FROM budget_categories bc
        JOIN budget_periods bp ON bc.period_id = bp.id
        WHERE bp.is_active = TRUE AND bc.name = 'Robert - Transport'
        ORDER BY bc.name
    """
    )

    desktop_result = cur.fetchone()
    if desktop_result:
        print(f"Desktop app WILL show Robert - Transport:")
        print(f"  ID: {desktop_result[0]}")
        print(f"  Name: {desktop_result[1]}")
        print(f"  Budgeted: {desktop_result[2]}")
        print(f"  Current: {desktop_result[3]}")
    else:
        print("Desktop app will NOT show Robert - Transport!")

    conn.close()


if __name__ == "__main__":
    try:
        check_transport_category()
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
