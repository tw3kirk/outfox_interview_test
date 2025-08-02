#!/usr/bin/env python3
"""
Local development runner for the Providers API.
Assumes Python 3.11 virtual environment is activated and dependencies are installed.
"""

import subprocess
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

def check_postgres_running():
    """Check if PostgreSQL is running"""
    try:
        # Try to connect to PostgreSQL
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            user="postgres",
            password="password"
        )
        conn.close()
        print("✅ PostgreSQL is running")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL is not running: {e}")
        print("Please start PostgreSQL and try again.")
        return False

def create_database_if_not_exists():
    """Create the providers database if it doesn't exist"""
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            user="postgres",
            password="password"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname='providers'")
        exists = cursor.fetchone()
        
        if not exists:
            print("Creating 'providers' database...")
            cursor.execute("CREATE DATABASE providers")
            print("✅ Database 'providers' created successfully")
        else:
            print("✅ Database 'providers' already exists")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def run_application():
    """Run the FastAPI application"""
    try:
        print("Starting FastAPI application...")
        subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except Exception as e:
        print(f"❌ Error running application: {e}")

def main():
    """Main function to run the local development setup"""
    print("🚀 Starting Providers API Local Development Setup")
    print("=" * 50)
    
    # Check PostgreSQL
    if not check_postgres_running():
        sys.exit(1)
    
    # Create database if needed
    if not create_database_if_not_exists():
        sys.exit(1)
    
    print("\n✅ All checks passed! Starting application...")
    print("📝 API will be available at: http://localhost:8000")
    print("📖 API documentation at: http://localhost:8000/docs")
    print("🔄 Press Ctrl+C to stop the application")
    print("=" * 50)
    
    # Run the application
    run_application()

if __name__ == "__main__":
    main() 