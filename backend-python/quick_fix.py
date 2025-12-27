#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick Database Fix - Choose solution"""

import os
from pathlib import Path


def update_env(database_url: str):
    """Update .env file"""
    env_file = Path('.env')

    content = []
    found = False

    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    content.append(f"DATABASE_URL={database_url}\n")
                    found = True
                else:
                    content.append(line)

    if not found:
        content.append(f"DATABASE_URL={database_url}\n")

    with open(env_file, 'w') as f:
        f.writelines(content)

    print("[+] .env file updated!")


def show_menu():
    """Display options"""
    print("\n" + "="*70)
    print("  DATABASE CONNECTION QUICK FIX")
    print("="*70)

    print("""
Current Issue:
  MySQL authentication failed with root user at 122.152.213.87
  Error: Access denied for user 'root'@'61.169.6.234'

Options:

  [1] Use ai_stock user (alternative MySQL user)
      URL: mysql+aiomysql://ai_stock:8pCNX3N3mzsHBLaW@122.152.213.87:3306/ai_stock

  [2] Use SQLite (local database - temporary workaround)
      URL: sqlite+aiosqlite:///./ai_stock.db
      Note: For testing only, not production

  [3] Retry with root (verify password first)
      URL: mysql+aiomysql://root:8pCNX3N3mzsHBLaW@122.152.213.87:3306/ai_stock

  [4] Use SQLite with demo data (complete testing setup)
      URL: sqlite+aiosqlite:///./ai_stock.db
      Action: Create sample data

  [5] Exit (no changes)

Select option [1-5]:
    """)


def create_sqlite_demo_data():
    """Create demo data for SQLite"""
    print("\n[*] Creating SQLite database with demo data...")

    try:
        import sqlite3
        from datetime import datetime, timedelta
        import random

        conn = sqlite3.connect('ai_stock.db')
        cursor = conn.cursor()

        # Create stocks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY,
                ts_code TEXT UNIQUE,
                symbol TEXT,
                name TEXT,
                area TEXT,
                industry TEXT,
                market TEXT,
                list_date TEXT
            )
        ''')

        # Create daily_quotes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_quotes (
                id INTEGER PRIMARY KEY,
                ts_code TEXT,
                trade_date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                vol REAL,
                amount REAL
            )
        ''')

        # Insert sample stocks
        sample_stocks = [
            ('000001.SZ', '平安', '平安银行', '深圳', '银行', 'A股', '1991-04-03'),
            ('000002.SZ', '万科', '万科A', '深圳', '房地产', 'A股', '1991-01-29'),
            ('600000.SH', '浦发', '浦发银行', '上海', '银行', 'A股', '1999-11-10'),
            ('600016.SH', '民生', '民生银行', '上海', '银行', 'A股', '2000-12-19'),
            ('600030.SH', '中信证', '中信证券', '上海', '证券', 'A股', '1995-10-05'),
        ]

        for ts_code, symbol, name, area, industry, market, list_date in sample_stocks:
            try:
                cursor.execute('''
                    INSERT INTO stocks (ts_code, symbol, name, area, industry, market, list_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (ts_code, symbol, name, area, industry, market, list_date))
            except sqlite3.IntegrityError:
                pass  # Stock already exists

        # Insert sample daily quotes
        start_date = datetime(2024, 1, 1)

        for stock_code, _, _, _, _, _, _ in sample_stocks:
            base_price = random.uniform(10, 100)

            for i in range(200):
                date = (start_date + timedelta(days=i)).strftime('%Y%m%d')

                price_change = random.uniform(-3, 3)
                high = base_price + price_change + random.uniform(0, 2)
                low = base_price + price_change - random.uniform(0, 2)
                close = base_price + price_change

                base_price = close

                volume = random.uniform(1000000, 50000000)
                amount = close * volume

                try:
                    cursor.execute('''
                        INSERT INTO daily_quotes
                        (ts_code, trade_date, open, high, low, close, vol, amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (stock_code, date, close-0.5, high, low, close, volume, amount))
                except sqlite3.IntegrityError:
                    pass

        conn.commit()
        conn.close()

        print("[+] SQLite database created with demo data!")
        print("    File: ai_stock.db")
        print("    Stocks: 5")
        print("    Daily records: 1000+")
        return True

    except Exception as e:
        print(f"[-] Error creating demo data: {e}")
        return False


def main():
    """Main function"""

    while True:
        show_menu()

        choice = input("\n> ").strip()

        if choice == '1':
            print("\n[*] Switching to ai_stock user...")
            url = "mysql+aiomysql://ai_stock:8pCNX3N3mzsHBLaW@122.152.213.87:3306/ai_stock"
            update_env(url)
            print("\n[!] Please verify that 'ai_stock' user exists in MySQL")
            print("    If it doesn't exist, create it with:")
            print("    CREATE USER 'ai_stock'@'%' IDENTIFIED BY '8pCNX3N3mzsHBLaW';")
            print("    GRANT ALL PRIVILEGES ON ai_stock.* TO 'ai_stock'@'%';")
            break

        elif choice == '2':
            print("\n[*] Switching to SQLite...")
            url = "sqlite+aiosqlite:///./ai_stock.db"
            update_env(url)
            print("\n[!] WARNING: SQLite is for testing only!")
            print("    For production, use MySQL")
            break

        elif choice == '3':
            print("\n[*] Retrying with root user...")
            url = "mysql+aiomysql://root:8pCNX3N3mzsHBLaW@122.152.213.87:3306/ai_stock"
            update_env(url)
            print("\n[!] Please verify MySQL password is correct")
            print("    If wrong, reset it with:")
            print("    ALTER USER 'root'@'%' IDENTIFIED BY '8pCNX3N3mzsHBLaW';")
            break

        elif choice == '4':
            print("\n[*] Creating SQLite with demo data...")
            url = "sqlite+aiosqlite:///./ai_stock.db"
            update_env(url)

            if create_sqlite_demo_data():
                print("\n[+] Setup complete!")
                print("    You can now run: python analyze_all_stocks.py")
            break

        elif choice == '5':
            print("\n[!] No changes made")
            break

        else:
            print("\n[-] Invalid option. Please try again.")
            continue

    print("\n" + "="*70)
    print("[*] Next steps:")
    print("    1. Restart the application: python -m uvicorn app.main:app --reload")
    print("    2. Run batch analysis: python analyze_all_stocks.py")
    print("    3. Or access API docs: http://127.0.0.1:8000/docs")
    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Cancelled by user")
    except Exception as e:
        print(f"\n[-] Error: {e}")
        import traceback
        traceback.print_exc()
