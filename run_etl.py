#!/usr/bin/env python3
"""
Manual ETL runner for troubleshooting
"""

import os
import sys
import subprocess

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Run the ETL process manually"""
    print("🚀 Running ETL process manually...")
    print("=" * 50)
    
    try:
        from app.etl import run_etl
        run_etl()
        print("\n✅ ETL process completed successfully!")
        
        # Check the results using subprocess to avoid SQLAlchemy issues
        print("\n🔍 Checking results...")
        try:
            result = subprocess.run(
                ["psql", "-h", "localhost", "-U", "postgres", "-d", "providers", "-c", "SELECT COUNT(*) FROM providers;"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                count = result.stdout.strip().split('\n')[2].strip()
                print(f"📊 Database now contains {count} provider records")
            else:
                print("❌ Could not check database results")
                print(f"Error: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error checking results: {e}")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure to install dependencies: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ ETL process failed: {e}")

if __name__ == "__main__":
    main() 