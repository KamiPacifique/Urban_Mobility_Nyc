# NYC Taxi Data - Backend API

Enterprise-level Flask backend with SQLite database for NYC Taxi Trip data analysis.

## System Architecture

```
+-------------------+         REST API         +-------------------+         +-------------------+
|                   | <---------------------> |                   | <-----> |                   |
|  HTML5 Frontend   |                         |   Flask Backend   |         |     SQLite DB     |
|   (frontend/)     |                         |   (backend/)      |         |   (nyc_taxi.db)   |
|                   |                         |                   |         |                   |
+-------------------+                         +-------------------+         +-------------------+
        ^                                              ^
        |                                              |
        |                                              |
        |                                              v
        |                                    +-------------------+
        |                                    | Data Processing   |
        |                                    | Scripts:          |
        |                                    | - convert_shp.py  |
        |                                    | - data_integration|
        |                                    | - data_cleaning   |
        |                                    | - load_data.py    |
        |                                    +-------------------+
        |                                              ^
        |                                              |
        |                                    +-------------------+
        |                                    |   Input Files     |
        |                                    | - tripdata.csv    |
        |                                    | - zone_lookup.csv |
        |                                    | - taxi_zones.shp  |
        |                                    +-------------------+
        |                                              ^
        |                                              |
        |                                    +-------------------+
        |                                    |   Log File        |
        |                                    | (cleaning_log.txt)|
        |                                    +-------------------+
```

## Data Flow Summary

1. **Extract**: Raw parquet data (7.6M trips) + Zone lookup + Shapefiles
2. **Transform**: 
   - Integrate zones with trips
   - Engineer 8 derived features
   - Clean outliers and validate data
3. **Load**: Import into normalized SQLite database (7.5M clean records)
4. **Serve**: Flask REST API with 12 endpoints
5. **Visualize**: Interactive frontend dashboard with 5 views

## Architecture

### Database Schema (Normalized)

**Dimension Tables:**
- `taxi_zones` - Borough and zone lookup data (265 zones)
- `zone_boundaries` - GeoJSON spatial boundaries for mapping

**Fact Table:**
- `trips` - Main trip records with raw fields + derived features

**Indexes:**
- Pickup datetime, location, hour, weekend for fast queries

### Derived Features (Feature Engineering)

1. **duration_min** - Trip duration in minutes
2. **fare_per_mile** - Revenue efficiency metric
3. **speed_mph** - Average trip speed
4. **tip_pct** - Tip as percentage of fare
5. **fare_per_min** - Time-based revenue
6. **pickup_hour** - Hour of day (0-23)
7. **pickup_dayofweek** - Day of week (0=Mon, 6=Sun)
8. **is_weekend** - Binary weekend flag

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Prepare Data Files

Ensure you have:
- `yellow_tripdata_2019-01.csv` (raw trip data)
- `taxi_zone_lookup.csv` (zone metadata)
- `taxi_zones/taxi_zones.shp` (spatial boundaries)

### 3. Run Data Pipeline

```bash
# Step 1: Convert shapefile to GeoJSON
python convert_shp.py

# Step 2: Integrate trip data with zone metadata
python data_integration.py

# Step 3: Clean the integrated data
python data_cleaning.py

# Step 4: Load everything into SQLite database
python load_data.py
```

### 4. Start API Server

```bash
python app.py
```

Server runs on `http://localhost:5000`

## API Endpoints

### Basic Endpoints

**GET `/api/health`**
- Health check

**GET `/api/stats`**
- Overall database statistics
- Date range, averages, total revenue

### Trip Endpoints

**GET `/api/trips`**
- List trips with pagination and filters
- Query params:
  - `page` - Page number (default: 1)
  - `per_page` - Results per page (default: 50)
  - `borough` - Filter by borough
  - `min_fare` - Minimum fare amount
  - `max_fare` - Maximum fare amount
  - `hour` - Filter by pickup hour (0-23)
  - `is_weekend` - 0 for weekday, 1 for weekend

**GET `/api/trips/<id>`**
- Get single trip details

### Zone Endpoints

**GET `/api/zones`**
- List all taxi zones

**GET `/api/zones/<location_id>`**
- Get specific zone with geometry

**GET `/api/zones/geojson`**
- All zones as GeoJSON FeatureCollection (for mapping)

### Analytics Endpoints

**GET `/api/analytics/hourly`**
- Trip statistics by hour of day
- Returns: trip count, avg fare, distance, duration, tip%, revenue per hour

**GET `/api/analytics/by-borough`**
- Trip statistics grouped by borough
- Shows which boroughs are most active

**GET `/api/analytics/weekend-vs-weekday`**
- Compare weekend vs weekday patterns

**GET `/api/analytics/top-routes`**
- Most popular pickup-dropoff combinations
- Query param: `limit` (default: 10)

**GET `/api/analytics/fare-distribution`**
- Fare amount distribution in buckets

## Example Requests

```bash
# Get overall stats
curl http://localhost:5000/api/stats

# Get trips from Manhattan
curl "http://localhost:5000/api/trips?borough=Manhattan&per_page=10"

# Get hourly patterns
curl http://localhost:5000/api/analytics/hourly

# Get top 20 routes
curl "http://localhost:5000/api/analytics/top-routes?limit=20"

# Get zones as GeoJSON for mapping
curl http://localhost:5000/api/zones/geojson
```

## Data Cleaning Log

The pipeline tracks:
- Initial record count
- Records removed (outliers, missing data)
- Final clean record count

Check `cleaning_log.txt` after running the pipeline.

## File Structure

```
backend/
├── app.py                      # Flask API server
├── database.py                 # Database schema & utilities
├── load_data.py               # Data loading pipeline
├── data_integration.py        # Link trips with zone metadata
├── data_cleaning.py           # Clean integrated data
├── convert_shp.py             # Convert shapefile to GeoJSON
├── requirements.txt           # Python dependencies
├── nyc_taxi.db               # SQLite database (created after load)
├── taxi_zone_lookup.csv      # Zone metadata
├── yellow_tripdata_2019-01.csv # Raw trip data
└── taxi_zones/               # Shapefile data
```

## Notes

- The database uses SQLite for simplicity and portability
- All endpoints return JSON
- CORS is enabled for frontend integration
- Data is indexed for query performance
- Large datasets are processed in chunks to manage memory