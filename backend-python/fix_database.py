#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database Connection Auto-Fixer

Diagnoses and attempts to fix database connectivity issues
"""

import os
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, r'C:\Users\02584\Desktop\新建文件夹\ai_stock\backend-python')


class DatabaseFixer:
    """数据库连接修复工具"""

    def __init__(self):
        self.env_file = Path('.env')
        self.current_url = None
        self.load_current_config()

    def load_current_config(self):
        """加载当前配置"""
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_URL='):
                        self.current_url = line.split('=', 1)[1].strip()
                        break

    def print_section(self, title):
        """打印分隔符"""
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")

    async def test_connection(self, url: str) -> tuple[bool, str]:
        """测试数据库连接

        Returns:
            (success, message)
        """
        try:
            from sqlalchemy.ext.asyncio import create_async_engine

            engine = create_async_engine(url, echo=False)

            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
                await engine.dispose()
                return True, "Connection successful"

        except Exception as e:
            error_msg = str(e)
            if "1045" in error_msg:
                return False, "Authentication failed (wrong password or user)"
            elif "Can't connect" in error_msg or "timeout" in error_msg:
                return False, "Cannot connect to server (network issue)"
            elif "Unknown database" in error_msg:
                return False, "Database does not exist"
            else:
                return False, f"Error: {error_msg}"

    def update_env(self, new_url: str):
        """更新 .env 文件"""
        content = []
        found = False

        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_URL='):
                        content.append(f"DATABASE_URL={new_url}\n")
                        found = True
                    else:
                        content.append(line)

        if not found:
            content.append(f"DATABASE_URL={new_url}\n")

        with open(self.env_file, 'w') as f:
            f.writelines(content)

    async def diagnose(self):
        """诊断数据库问题"""

        self.print_section("DATABASE CONNECTION DIAGNOSIS")

        print("[*] Current Configuration:")
        if self.current_url:
            print(f"    Database URL: {self.current_url}")
        else:
            print("    [!] No DATABASE_URL found in .env")

        print("\n[*] Testing current configuration...")
        if self.current_url:
            success, msg = await self.test_connection(self.current_url)
            if success:
                print(f"    [+] {msg}")
                return True
            else:
                print(f"    [-] {msg}")

        # Try alternative configurations
        print("\n[*] Testing alternative credentials...")

        alternatives = [
            ("mysql+aiomysql://ai_stock:8pCNX3N3mzsHBLaW@122.152.213.87:3306/ai_stock", "ai_stock user"),
            ("mysql+aiomysql://root:@122.152.213.87:3306/ai_stock", "root with no password"),
            ("sqlite+aiosqlite:///./ai_stock.db", "SQLite (local)"),
        ]

        for url, desc in alternatives:
            print(f"\n    Testing: {desc}")
            success, msg = await self.test_connection(url)
            if success:
                print(f"    [+] SUCCESS! {msg}")
                return url
            else:
                print(f"    [-] {msg}")

        return None

    async def fix(self, new_url: str = None):
        """修复数据库连接"""

        self.print_section("DATABASE CONNECTION FIX")

        # First diagnose
        result = await self.diagnose()

        if result is True:
            print("\n[+] Database connection is already working!")
            print("    No fix needed.")
            return True

        if isinstance(result, str):
            new_url = result
            print(f"\n[+] Found working configuration: {new_url}")
        else:
            if not new_url:
                print("\n[-] Could not find working database configuration")
                self.suggest_solutions()
                return False

        # Confirm update
        print("\n[*] Would you like to update the .env file?")
        print(f"    New URL: {new_url}")
        print("    (Enter 'y' to confirm, 'n' to skip)")

        response = input("\n  > ").strip().lower()

        if response == 'y':
            self.update_env(new_url)
            print("\n[+] .env file updated successfully!")
            print("    [!] Please restart the application for changes to take effect")
            print("    Command: python -m uvicorn app.main:app --reload")
            return True
        else:
            print("\n[!] Update cancelled")
            return False

    def suggest_solutions(self):
        """建议解决方案"""

        self.print_section("SUGGESTED SOLUTIONS")

        print("""
1. VERIFY MYSQL CREDENTIALS
   - Check MySQL user exists: root@122.152.213.87
   - Verify password: 8pCNX3N3mzsHBLaW
   - Check user has remote access permission (%)

2. RESET MYSQL PASSWORD (if you have admin access)
   mysql -u root -p
   > ALTER USER 'root'@'%' IDENTIFIED BY '8pCNX3N3mzsHBLaW';
   > FLUSH PRIVILEGES;

3. CREATE NEW DATABASE USER
   > CREATE USER 'ai_stock'@'%' IDENTIFIED BY '8pCNX3N3mzsHBLaW';
   > GRANT ALL PRIVILEGES ON ai_stock.* TO 'ai_stock'@'%';
   > FLUSH PRIVILEGES;

4. USE SQLITE AS TEMPORARY WORKAROUND
   - Update .env: DATABASE_URL=sqlite+aiosqlite:///./ai_stock.db
   - This allows testing without MySQL
   - Not recommended for production

5. CHECK NETWORK CONNECTIVITY
   - Ping: ping 122.152.213.87
   - Telnet: telnet 122.152.213.87 3306
   - Check firewall rules

6. INITIALIZE DATABASE
   - If database exists but is empty:
   - mysql < database/schema.sql

Need more help? See DATABASE_FIX_GUIDE.md
        """)


async def main():
    """Main function"""

    fixer = DatabaseFixer()

    print("="*70)
    print("  DATABASE CONNECTION AUTO-FIXER")
    print("="*70)

    # Run diagnosis and fix
    success = await fixer.fix()

    if success:
        print("\n[+] Database configuration fixed!")
        print("    Next steps:")
        print("    1. Restart the FastAPI application")
        print("    2. Run: python analyze_all_stocks.py")
    else:
        print("\n[-] Could not auto-fix database connection")
        print("    Please follow the suggestions above")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[!] Cancelled by user")
    except Exception as e:
        print(f"\n[-] Error: {e}")
        import traceback
        traceback.print_exc()
