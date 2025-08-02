import pandas as pd
import os
from math import radians, cos, sin, asin, sqrt
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# Load the zip codes data once at module level
_zip_data = None

def load_zip_data():
    """Load the zip codes data from CSV file, forcing zip code as string"""
    global _zip_data
    if _zip_data is None:
        try:
            csv_file = "USZipsWithLatLon_20231227.csv"
            if os.path.exists(csv_file):
                _zip_data = pd.read_csv(csv_file, dtype={"postal code": str})
                print(f"✅ Loaded {len(_zip_data)} zip codes from {csv_file}")
            else:
                print(f"⚠️  Zip codes CSV file {csv_file} not found")
                _zip_data = pd.DataFrame()
        except Exception as e:
            print(f"⚠️  Error loading zip codes data: {e}")
            _zip_data = pd.DataFrame()
    return _zip_data

def geocode_zip_code_nominatim(zip_code: str) -> tuple:
    """Geocode a zip code using Nominatim (for API endpoint)"""
    try:
        geolocator = Nominatim(user_agent="providers_api")
        location_string = f"{zip_code}, USA"
        
        location = geolocator.geocode(location_string, timeout=10)
        
        if location:
            return location.latitude, location.longitude
        else:
            print(f"⚠️  Could not geocode zip code with Nominatim: {zip_code}")
            return None, None
            
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"⚠️  Nominatim geocoding timeout/unavailable for zip code {zip_code}: {e}")
        return None, None
    except Exception as e:
        print(f"⚠️  Nominatim geocoding error for zip code {zip_code}: {e}")
        return None, None

def geocode_zip_code(zip_code: str) -> tuple:
    """Geocode a zip code using the CSV data (for ETL)"""
    try:
        zip_data = load_zip_data()
        if zip_data.empty:
            return None, None
        
        # Clean the zip code and always use string for matching
        zip_code_str = str(zip_code).zfill(5)
        
        # Try to find a match by zip code (as string)
        matches = zip_data[zip_data['postal code'] == zip_code_str]
        
        if len(matches) > 0:
            # Take the first match
            lat = float(matches.iloc[0]['latitude'])
            lng = float(matches.iloc[0]['longitude'])
            return lat, lng
        else:
            print(f"⚠️  Could not find coordinates for zip code: {zip_code_str}")
            return None, None
            
    except Exception as e:
        print(f"⚠️  Geocoding error for zip code {zip_code}: {e}")
        return None, None

def geocode_location_simple(city, state, zip_code):
    """Geocode a location using zip code first, then fallback to city/state"""
    try:
        # First try zip code geocoding
        if zip_code:
            lat, lng = geocode_zip_code(zip_code)
            if lat and lng:
                return lat, lng
        
        # Fallback to city/state if zip code not found
        # This would use the old uscities.csv approach if needed
        print(f"⚠️  Could not geocode location: {city}, {state} {zip_code}")
        return None, None
                
    except Exception as e:
        print(f"⚠️  Geocoding error for {city}, {state}: {e}")
        return None, None

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers using Haversine formula"""
    try:
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        distance = c * r
        return distance
    except Exception as e:
        print(f"⚠️  Distance calculation error: {e}")
        return float('inf')  # Return infinity if calculation fails

def is_within_radius(lat1: float, lon1: float, lat2: float, lon2: float, radius_km: float) -> bool:
    """Check if two points are within the specified radius"""
    distance = calculate_distance(lat1, lon1, lat2, lon2)
    return distance <= radius_km 