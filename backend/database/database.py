import sqlite3
import json
from datetime import datetime

DB_NAME = 'nyc_taxi.db'

def get_db_connection():
    """Get a database connection"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Returns rows as dictionaries
    return conn

def init_database():
    """Initialize the database with normalized schema"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Dimension Table: Taxi Zones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS taxi_zones (
            location_id INTEGER PRIMARY KEY,
            borough TEXT,
            zone TEXT,
            service_zone TEXT
        )
    ''')
    
    # Dimension Table: Spatial Boundaries (GeoJSON)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zone_boundaries (
            location_id INTEGER PRIMARY KEY,
            geometry TEXT NOT NULL,
            FOREIGN KEY (location_id) REFERENCES taxi_zones(location_id)
        )
    ''')
    
    # Fact Table: Trip Records
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pickup_datetime TIMESTAMP NOT NULL,
            dropoff_datetime TIMESTAMP NOT NULL,
            pickup_location_id INTEGER,
            dropoff_location_id INTEGER,
            passenger_count INTEGER,
            trip_distance REAL,
            fare_amount REAL,
            tip_amount REAL,
            tolls_amount REAL,
            total_amount REAL,
            payment_type INTEGER,
            rate_code_id INTEGER,
            
            -- Derived Features
            duration_min REAL,
            fare_per_mile REAL,
            speed_mph REAL,
            tip_pct REAL,
            fare_per_min REAL,
            pickup_hour INTEGER,
            pickup_dayofweek INTEGER,
            is_weekend INTEGER,
            
            FOREIGN KEY (pickup_location_id) REFERENCES taxi_zones(location_id),
            FOREIGN KEY (dropoff_location_id) REFERENCES taxi_zones(location_id)
        )
    ''')
    
    # Create indexes for efficient querying
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pickup_datetime 
        ON trips(pickup_datetime)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pickup_location 
        ON trips(pickup_location_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_dropoff_location 
        ON trips(dropoff_location_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pickup_hour 
        ON trips(pickup_hour)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_is_weekend 
        ON trips(is_weekend)
    ''')
    
    # Summary/Analytics Table for faster aggregations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trip_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            hour INTEGER,
            location_id INTEGER,
            trip_count INTEGER,
            avg_fare REAL,
            avg_distance REAL,
            avg_duration REAL,
            total_revenue REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(" Database schema initialized successfully")

def clear_database():
    """Clear all data from tables (useful for re-imports)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM trips')
    cursor.execute('DELETE FROM zone_boundaries')
    cursor.execute('DELETE FROM taxi_zones')
    cursor.execute('DELETE FROM trip_summary')
    
    conn.commit()
    conn.close()
    print("Database cleared")

if __name__ == "__main__":
    print("Initializing NYC Taxi Database...")
    init_database()
