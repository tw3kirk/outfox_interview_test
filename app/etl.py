import pandas as pd
import os
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from decimal import Decimal, InvalidOperation
from .database import engine, SessionLocal
from .models import Provider, Base
from .geocoding import geocode_zip_code

def create_tables():
    """Create all tables in the database"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

def load_csv_data():
    """Load data from CSV file and populate the database"""
    csv_file = "MUP_INP_RY24_P03_V10_DY22_PrvSvc.csv"
    
    if not os.path.exists(csv_file):
        print(f"CSV file {csv_file} not found!")
        return
    
    # Try different approaches to read the CSV file
    df = None
    
    # Method 1: Try with error handling
    try:
        print("Trying to read CSV with error handling...")
        df = pd.read_csv(
            csv_file,
            encoding='utf-8',
            on_bad_lines='skip',
            low_memory=False
        )
        print("✅ Successfully read CSV with error handling")
    except Exception as e:
        print(f"❌ Error with error handling: {e}")
        
        # Method 2: Try with different encoding
        try:
            print("Trying with latin-1 encoding...")
            df = pd.read_csv(
                csv_file,
                encoding='latin-1',
                on_bad_lines='skip',
                low_memory=False
            )
            print("✅ Successfully read CSV with latin-1 encoding")
        except Exception as e:
            print(f"❌ Error with latin-1 encoding: {e}")
            
            # Method 3: Try with cp1252 encoding
            try:
                print("Trying with cp1252 encoding...")
                df = pd.read_csv(
                    csv_file,
                    encoding='cp1252',
                    on_bad_lines='skip',
                    low_memory=False
                )
                print("✅ Successfully read CSV with cp1252 encoding")
            except Exception as e:
                print(f"❌ Error with cp1252 encoding: {e}")
                
                # Method 4: Last resort - read with errors='replace'
                try:
                    print("Trying with error replacement...")
                    df = pd.read_csv(
                        csv_file,
                        encoding='utf-8',
                        on_bad_lines='skip',
                        low_memory=False,
                        error_bad_lines=False,
                        warn_bad_lines=False
                    )
                    print("✅ Successfully read CSV with error replacement")
                except Exception as e:
                    print(f"❌ All methods failed: {e}")
                    return
    
    if df is None:
        print("❌ Failed to read CSV file with any method")
        return
    
    print(f"📊 Loaded {len(df)} rows from CSV file")
    
    # Create a mapping of unique zip codes to coordinates
    print("🔍 Creating unique zip code mapping...")
    unique_zip_codes = df['Rndrng_Prvdr_Zip5'].astype(str).str.zfill(5).unique()
    zip_code_coordinates = {}
    
    print(f"📍 Found {len(unique_zip_codes)} unique zip codes to geocode")
    
    # Geocode each unique zip code using simple mapping
    geocoded_count = 0
    for zip_code_str in unique_zip_codes:
        latitude, longitude = geocode_zip_code(zip_code_str)
        if latitude and longitude:
            zip_code_coordinates[zip_code_str] = (latitude, longitude)
            geocoded_count += 1
        if geocoded_count % 100 == 0:
            print(f"🌍 Geocoded {geocoded_count}/{len(unique_zip_codes)} unique zip codes...")
    print(f"✅ Successfully geocoded {geocoded_count} unique zip codes")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Test database connection
        print("Testing database connection...")
        db.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        
        # Clear existing data
        print("Clearing existing data...")
        deleted_count = db.query(Provider).delete()
        db.commit()
        print(f"✅ Cleared {deleted_count} existing records")
        
        # Process each row
        processed_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                provider_id = str(row['Rndrng_Prvdr_CCN']).strip()
                city = str(row['Rndrng_Prvdr_City']).strip()
                state = str(row['Rndrng_Prvdr_State_Abrvtn']).strip()
                zip_code_raw = str(row['Rndrng_Prvdr_Zip5']).strip()
                zip_code_str = zip_code_raw.zfill(5)
                try:
                    zip_code = int(zip_code_raw)
                except Exception:
                    print(f"⚠️  Skipping row {index+1}: Invalid zip code '{zip_code_raw}'")
                    error_count += 1
                    continue
                try:
                    ms_drg_definition = int(row['DRG_Cd'])
                except Exception:
                    print(f"⚠️  Skipping row {index+1}: Invalid ms_drg_definition '{row['DRG_Cd']}'")
                    error_count += 1
                    continue
                try:
                    avg_covered = Decimal(str(row['Avg_Submtd_Cvrd_Chrg']))
                    avg_total = Decimal(str(row['Avg_Tot_Pymt_Amt']))
                    avg_medicare = Decimal(str(row['Avg_Mdcr_Pymt_Amt']))
                except (InvalidOperation, Exception):
                    print(f"⚠️  Skipping row {index+1}: Invalid decimal value(s)")
                    error_count += 1
                    continue
                
                # Get coordinates from the zip code mapping
                latitude, longitude = zip_code_coordinates.get(zip_code_str, (None, None))
                
                provider = Provider(
                    provider_id=provider_id,
                    provider_name=str(row['Rndrng_Prvdr_Org_Name']).strip(),
                    provider_city=city,
                    provider_state=state,
                    provider_zip_code=zip_code,
                    ms_drg_definition=ms_drg_definition,
                    total_discharges=int(float(row['Tot_Dschrgs'])),
                    average_covered_charges=avg_covered,
                    average_total_payments=avg_total,
                    average_medicare_payments=avg_medicare,
                    latitude=latitude,
                    longitude=longitude
                )
                
                db.add(provider)
                processed_count += 1
                
                if processed_count % 1000 == 0:
                    db.commit()
                    print(f"Processed {processed_count} records...")
                
            except Exception as e:
                error_count += 1
                print(f"Error processing row {index + 1}: {e}")
                print(f"Row data: {row.to_dict()}")
                continue
        
        db.commit()
        print(f"✅ Successfully processed {processed_count} records into the database")
        if error_count > 0:
            print(f"⚠️  {error_count} records had errors and were skipped")
        
    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
        if db.is_active:
            db.rollback()
    except Exception as e:
        print(f"❌ Error loading CSV data: {e}")
        if db.is_active:
            db.rollback()
    finally:
        db.close()

def run_etl():
    """Run the complete ETL process"""
    print("Creating database tables...")
    create_tables()
    
    print("Loading CSV data...")
    load_csv_data()
    
    print("ETL process completed!") 