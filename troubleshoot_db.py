#!/usr/bin/env python3
"""
Troubleshooting script for database and ETL issues
"""

import os
import sys
import subprocess
from pathlib import Path

def check_postgresql():
    """Check if PostgreSQL is running and accessible"""
    print("🔍 Checking PostgreSQL...")
    
    try:
        # Test basic connection
        result = subprocess.run(
            ["psql", "-h", "localhost", "-U", "postgres", "-d", "postgres", "-c", "SELECT 1;"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ PostgreSQL is running and accessible")
            return True
        else:
            print(f"❌ PostgreSQL connection failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ psql command not found. PostgreSQL may not be installed.")
        return False
    except Exception as e:
        print(f"❌ Error checking PostgreSQL: {e}")
        return False

def check_database():
    """Check if the providers database exists and is accessible"""
    print("\n🔍 Checking providers database...")
    
    try:
        # Test connection to providers database
        result = subprocess.run(
            ["psql", "-h", "localhost", "-U", "postgres", "-d", "providers", "-c", "SELECT 1;"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ providers database exists and is accessible")
            return True
        else:
            print(f"❌ providers database connection failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking providers database: {e}")
        return False

def check_tables():
    """Check if the providers table exists and has data"""
    print("\n🔍 Checking providers table...")
    
    try:
        # Check if table exists
        result = subprocess.run(
            ["psql", "-h", "localhost", "-U", "postgres", "-d", "providers", "-c", "\\dt providers;"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "providers" in result.stdout:
            print("✅ providers table exists")
            
            # Check row count
            count_result = subprocess.run(
                ["psql", "-h", "localhost", "-U", "postgres", "-d", "providers", "-c", "SELECT COUNT(*) FROM providers;"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if count_result.returncode == 0:
                count = count_result.stdout.strip().split('\n')[2].strip()
                print(f"📊 providers table has {count} rows")
                return int(count) if count.isdigit() else 0
            else:
                print(f"❌ Error counting rows: {count_result.stderr}")
                return 0
        else:
            print("❌ providers table does not exist")
            return 0
            
    except Exception as e:
        print(f"❌ Error checking providers table: {e}")
        return 0

def check_csv_file():
    """Check if the CSV file exists and is readable"""
    print("\n🔍 Checking CSV file...")
    
    csv_file = Path("MUP_INP_RY24_P03_V10_DY22_PrvSvc.csv")
    
    if not csv_file.exists():
        print("❌ CSV file not found")
        return False
    
    print(f"✅ CSV file exists ({csv_file.stat().st_size} bytes)")
    
    try:
        # Try to read first few lines
        with open(csv_file, 'r', encoding='utf-8') as f:
            lines = [next(f) for _ in range(5)]
        print("✅ CSV file is readable")
        print(f"📝 First line: {lines[0][:100]}...")
        return True
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return False

def check_dependencies():
    """Check if required Python packages are installed"""
    print("\n🔍 Checking Python dependencies...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'psycopg2',
        'pandas',
        'pydantic',
        'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    else:
        print("✅ All dependencies installed")
        return True

def run_etl_test():
    """Test the ETL process"""
    print("\n🔍 Testing ETL process...")
    
    try:
        # Add current directory to Python path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from app.etl import run_etl
        run_etl()
        return True
    except Exception as e:
        print(f"❌ ETL test failed: {e}")
        return False

def main():
    """Run all troubleshooting checks"""
    print("🚀 Providers API Database Troubleshooting")
    print("=" * 50)
    
    # Run all checks
    postgres_ok = check_postgresql()
    deps_ok = check_dependencies()
    csv_ok = check_csv_file()
    
    if postgres_ok:
        db_ok = check_database()
        if db_ok:
            row_count = check_tables()
        else:
            row_count = 0
    else:
        db_ok = False
        row_count = 0
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY:")
    print(f"PostgreSQL: {'✅' if postgres_ok else '❌'}")
    print(f"Dependencies: {'✅' if deps_ok else '❌'}")
    print(f"CSV File: {'✅' if csv_ok else '❌'}")
    print(f"Database: {'✅' if db_ok else '❌'}")
    print(f"Data in table: {row_count} rows")
    
    if row_count == 0 and all([postgres_ok, deps_ok, csv_ok, db_ok]):
        print("\n🔧 RECOMMENDATIONS:")
        print("1. Run the ETL process manually:")
        print("   pip install -r requirements.txt")
        print("   python -c \"from app.etl import run_etl; run_etl()\"")
        print("\n2. Or use Docker (recommended):")
        print("   docker compose up --build")
    
    elif not postgres_ok:
        print("\n🔧 RECOMMENDATIONS:")
        print("1. Install PostgreSQL:")
        print("   brew install postgresql")
        print("   brew services start postgresql")
        print("\n2. Or use Docker:")
        print("   docker compose up --build")

if __name__ == "__main__":
    main() 