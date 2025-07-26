#!/usr/bin/env python3
"""
Preview what the enhanced budget population would do
This is a safe, read-only script that shows what would happen without making changes
"""

import os
import json
from datetime import date
from dateutil.relativedelta import relativedelta
from pathlib import Path


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


def get_next_month_info():
    """Calculate next month's period name and dates"""
    today = date.today()
    next_month = today + relativedelta(months=1)

    period_name = next_month.strftime("%B %Y")  # e.g., "September 2025"

    # Budget period starts on 24th of current month (salary day)
    # and runs until the end of next month
    start_date = today.replace(day=24)

    # End date is last day of next month
    month_after = next_month + relativedelta(months=1)
    end_date = month_after.replace(day=1) - relativedelta(days=1)

    return period_name, start_date, end_date


def preview_budget_population():
    """Preview what the budget population would do"""
    print("=" * 60)
    print("BUDGET POPULATION PREVIEW (READ-ONLY)")
    print(f"Preview date: {date.today().strftime('%Y-%m-%d')}")
    print("=" * 60)

    # Load settings
    settings = load_settings()
    if not settings:
        print("❌ Could not load settings")
        return

    # Calculate next month info
    period_name, start_date, end_date = get_next_month_info()
    print(f"\n📅 WOULD CREATE PERIOD:")
    print(f"   • Name: {period_name}")
    print(f"   • Start: {start_date} (salary day)")
    print(f"   • End: {end_date}")
    print(f"   • Would become: ACTIVE")

    # Preview budget categories
    budget_categories = settings.get("budget_categories", {})
    if budget_categories:
        print(f"\n💰 WOULD CREATE BUDGET CATEGORIES:")
        total_budget = 0
        category_count = 0

        for user, categories in budget_categories.items():
            print(f"\n   {user}:")
            user_total = 0

            for category, amount in categories.items():
                if isinstance(amount, dict):
                    # Handle nested categories like Town Council
                    for sub_category, sub_amount in amount.items():
                        category_name = f"{user} - {category} - {sub_category}"
                        print(f"      • {category_name}: R{sub_amount}")
                        user_total += float(sub_amount)
                        category_count += 1
                else:
                    category_name = f"{user} - {category}"
                    print(f"      • {category_name}: R{amount}")
                    user_total += float(amount)
                    category_count += 1

            print(f"   {user} subtotal: R{user_total:.2f}")
            total_budget += user_total

        print(f"\n   TOTAL CATEGORIES: {category_count}")
        print(f"   TOTAL BUDGET: R{total_budget:.2f}")
    else:
        print(f"\n⚠  No budget categories found in settings")

    # Preview income
    income_data = settings.get("Income", {})
    if income_data:
        print(f"\n💵 WOULD ADD MONTHLY INCOME:")
        total_income = 0

        for user, salary in income_data.items():
            if salary > 0:
                print(f"   • {user}: R{salary} salary")
                print(f"     Would be added to: {user} - Bank Zero Cheque")
                total_income += float(salary)

        print(f"\n   TOTAL INCOME: R{total_income:.2f}")
    else:
        print(f"\n⚠  No income data found in settings")

    # Preview period activation
    print(f"\n🔄 WOULD ACTIVATE PERIOD:")
    print(f"   • Current active period would be: DEACTIVATED")
    print(f"   • {period_name} would become: ACTIVE")

    # Summary
    print(f"\n" + "=" * 60)
    print("PREVIEW SUMMARY")
    print("=" * 60)
    print(f"Target period: {period_name}")
    print(
        f"Categories to create: {category_count if budget_categories else 0}"
    )
    print(
        f"Total budget: R{total_budget:.2f}"
        if budget_categories
        else "Total budget: R0.00"
    )
    print(
        f"Total income: R{total_income:.2f}"
        if income_data
        else "Total income: R0.00"
    )
    print(f"Period activation: {period_name} would become active")

    print(f"\n🔍 This is a PREVIEW ONLY - no actual changes would be made")
    print(
        f"🚀 The real automation will run on {period_name.split()[0]} 24th at midnight"
    )


def main():
    print("Enhanced Budget Population Preview Tool")
    print("This tool shows what WOULD happen without making any changes")

    # Load environment (though we don't need DB for preview)
    load_env()

    # Run preview
    preview_budget_population()

    print(f"\n✅ Preview completed successfully!")


if __name__ == "__main__":
    main()
