import pandas as pd
import sqlite3
from database import get_db_connection, init_database, DB_NAME
import os
import json

def load_taxi_zones(lookup_file='taxi_zone_lookup.csv'):
    """Load taxi zone lookup data into database"""
    if not os.path.exists(lookup_file):
        print(f"Warning: {lookup_file} not found")
        return
    
    print(f"Loading taxi zones from {lookup_file}...")
    df = pd.read_csv(lookup_file)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for _, row in df.iterrows():
        cursor.execute('''
            INSERT OR REPLACE INTO taxi_zones (location_id, borough, zone, service_zone)
            VALUES (?, ?, ?, ?)
        ''', (
            row['LocationID'],
            row['Borough'],
            row['Zone'],
            row.get('service_zone', None)
        ))
    
    conn.commit()
    zones_count = cursor.execute('SELECT COUNT(*) FROM taxi_zones').fetchone()[0]
    conn.close()
    print(f"✓ Loaded {zones_count} taxi zones")

def load_zone_boundaries(geojson_file='taxi_zones.geojson'):
    """Load spatial boundaries from GeoJSON into database"""
    if not os.path.exists(geojson_file):
        print(f"Warning: {geojson_file} not found. Run convert_shp.py first.")
        return
    
    print(f"Loading zone boundaries from {geojson_file}...")
    
    with open(geojson_file, 'r') as f:
        geojson_data = json.load(f)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for feature in geojson_data['features']:
        location_id = feature['properties']['locationid']
        geometry = json.dumps(feature['geometry'])
        
        cursor.execute('''
            INSERT OR REPLACE INTO zone_boundaries (location_id, geometry)
            VALUES (?, ?)
        ''', (location_id, geometry))
    
    conn.commit()
    boundary_count = cursor.execute('SELECT COUNT(*) FROM zone_boundaries').fetchone()[0]
    conn.close()
    print(f"✓ Loaded {boundary_count} zone boundaries")

def load_trips_data(cleaned_file='final_cleaned_data.csv', batch_size=10000):
    """Load cleaned trip data into database in batches"""
    if not os.path.exists(cleaned_file):
        print(f"Error: {cleaned_file} not found. Run data_integration.py and data_cleaning.py first.")
        return
    
    print(f"Loading trip data from {cleaned_file}...")
    print("This may take several minutes...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    total_inserted = 0
    
    # Read in chunks to handle large files
    for chunk_num, chunk in enumerate(pd.read_csv(cleaned_file, chunksize=batch_size)):
        records = []
        
        for _, row in chunk.iterrows():
            records.append((
                row.get('tpep_pickup_datetime'),
                row.get('tpep_dropoff_datetime'),
                row.get('PULocationID'),
                row.get('DOLocationID'),
                row.get('passenger_count'),
                row.get('trip_distance'),
                row.get('fare_amount'),
                row.get('tip_amount'),
                row.get('tolls_amount'),
                row.get('total_amount'),
                row.get('payment_type'),
                row.get('RatecodeID'),
                # Derived features
                row.get('duration_min'),
                row.get('fare_per_mile'),
                row.get('speed_mph'),
                row.get('tip_pct'),
                row.get('fare_per_min'),
                row.get('pickup_hour'),
                row.get('pickup_dayofweek'),
                row.get('is_weekend')
            ))
        
        cursor.executemany('''
            INSERT INTO trips (
                pickup_datetime, dropoff_datetime, pickup_location_id, dropoff_location_id,
                passenger_count, trip_distance, fare_amount, tip_amount, tolls_amount,
                total_amount, payment_type, rate_code_id, duration_min, fare_per_mile,
                speed_mph, tip_pct, fare_per_min, pickup_hour, pickup_dayofweek, is_weekend
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', records)
        
        conn.commit()
        total_inserted += len(records)
        print(f"  Inserted batch {chunk_num + 1}: {total_inserted} total records")
    
    conn.close()
    print(f"✓ Successfully loaded {total_inserted} trip records")

def main():
    """Main data loading pipeline"""
    print("=== NYC Taxi Data Loading Pipeline ===\n")
    
    # Step 1: Initialize database
    init_database()
    
    # Step 2: Load dimension tables
    load_taxi_zones()
    load_zone_boundaries()
    
    # Step 3: Load fact table (trips)
    load_trips_data()
    
    # Step 4: Verify data
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("\n=== Database Summary ===")
    zones = cursor.execute('SELECT COUNT(*) FROM taxi_zones').fetchone()[0]
    boundaries = cursor.execute('SELECT COUNT(*) FROM zone_boundaries').fetchone()[0]
    trips = cursor.execute('SELECT COUNT(*) FROM trips').fetchone()[0]
    
    print(f"Taxi Zones: {zones}")
    print(f"Zone Boundaries: {boundaries}")
    print(f"Trip Records: {trips}")
    
    if trips > 0:
        sample = cursor.execute('SELECT * FROM trips LIMIT 1').fetchone()
        print(f"\nSample trip record: {dict(sample)}")
    
    conn.close()
    print("\n✓ Data loading complete!")

if __name__ == "__main__":
    main()
