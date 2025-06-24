#!/usr/bin/env python3
import os
import psycopg

# Test database connection
def test_connection():
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("ERROR: DATABASE_URL environment variable not set")
            return False
        
        print(f"Connecting to database...")
        conn = psycopg.connect(database_url)
        cur = conn.cursor()
        
        # Test basic query
        cur.execute('SELECT version();')
        version = cur.fetchone()
        print(f"Connected successfully! PostgreSQL version: {version[0]}")
        
        # Test creating a simple table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100)
            )
        ''')
        
        print("Test table created successfully")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()