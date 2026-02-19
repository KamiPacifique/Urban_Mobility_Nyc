from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_db_connection
import json
from datetime import datetime

app = Flask(__name__)
# Configure CORS with explicit settings
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ==================== UTILITY FUNCTIONS ====================

def dict_factory(cursor, row):
    """Convert database row to dictionary"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# ==================== BASIC ENDPOINTS ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'NYC Taxi API is running'})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall database statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    stats['total_trips'] = cursor.execute('SELECT COUNT(*) FROM trips').fetchone()[0]
    stats['total_zones'] = cursor.execute('SELECT COUNT(*) FROM taxi_zones').fetchone()[0]
    
    # Get date range
    date_range = cursor.execute('''
        SELECT MIN(pickup_datetime) as min_date, MAX(pickup_datetime) as max_date 
        FROM trips
    ''').fetchone()
    stats['date_range'] = {'start': date_range[0], 'end': date_range[1]}
    
    # Average metrics
    avg_metrics = cursor.execute('''
        SELECT 
            AVG(fare_amount) as avg_fare,
            AVG(trip_distance) as avg_distance,
            AVG(duration_min) as avg_duration,
            AVG(tip_pct) as avg_tip_pct,
            SUM(total_amount) as total_revenue
        FROM trips
    ''').fetchone()
    
    stats['averages'] = {
        'fare': round(avg_metrics[0], 2) if avg_metrics[0] else 0,
        'distance': round(avg_metrics[1], 2) if avg_metrics[1] else 0,
        'duration': round(avg_metrics[2], 2) if avg_metrics[2] else 0,
        'tip_percentage': round(avg_metrics[3], 2) if avg_metrics[3] else 0,
        'total_revenue': round(avg_metrics[4], 2) if avg_metrics[4] else 0
    }
    
    conn.close()
    return jsonify(stats)

# ==================== TRIPS ENDPOINTS ====================

@app.route('/api/trips', methods=['GET'])
def get_trips():
    """Get trips with optional filtering and pagination"""
    # Query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    borough = request.args.get('borough')
    min_fare = request.args.get('min_fare', type=float)
    max_fare = request.args.get('max_fare', type=float)
    hour = request.args.get('hour', type=int)
    is_weekend = request.args.get('is_weekend', type=int)
    
    offset = (page - 1) * per_page
    
    # Build query
    query = '''
        SELECT 
            t.*,
            pz.borough as pickup_borough,
            pz.zone as pickup_zone,
            dz.borough as dropoff_borough,
            dz.zone as dropoff_zone
        FROM trips t
        LEFT JOIN taxi_zones pz ON t.pickup_location_id = pz.location_id
        LEFT JOIN taxi_zones dz ON t.dropoff_location_id = dz.location_id
        WHERE 1=1
    '''
    params = []
    
    if borough:
        query += ' AND (pz.borough = ? OR dz.borough = ?)'
        params.extend([borough, borough])
    
    if min_fare:
        query += ' AND t.fare_amount >= ?'
        params.append(min_fare)
    
    if max_fare:
        query += ' AND t.fare_amount <= ?'
        params.append(max_fare)
    
    if hour is not None:
        query += ' AND t.pickup_hour = ?'
        params.append(hour)
    
    if is_weekend is not None:
        query += ' AND t.is_weekend = ?'
        params.append(is_weekend)
    
    query += ' ORDER BY t.pickup_datetime DESC LIMIT ? OFFSET ?'
    params.extend([per_page, offset])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    trips = cursor.execute(query, params).fetchall()
    trips_list = [dict(row) for row in trips]
    
    # Get total count for pagination
    count_query = query.split('ORDER BY')[0].replace('SELECT t.*, pz.borough as pickup_borough, pz.zone as pickup_zone, dz.borough as dropoff_borough, dz.zone as dropoff_zone', 'SELECT COUNT(*)')
    total = cursor.execute(count_query, params[:-2]).fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'trips': trips_list,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    })

@app.route('/api/trips/<int:trip_id>', methods=['GET'])
def get_trip(trip_id):
    """Get a single trip by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    trip = cursor.execute('''
        SELECT 
            t.*,
            pz.borough as pickup_borough,
            pz.zone as pickup_zone,
            dz.borough as dropoff_borough,
            dz.zone as dropoff_zone
        FROM trips t
        LEFT JOIN taxi_zones pz ON t.pickup_location_id = pz.location_id
        LEFT JOIN taxi_zones dz ON t.dropoff_location_id = dz.location_id
        WHERE t.id = ?
    ''', (trip_id,)).fetchone()
    
    conn.close()
    
    if trip:
        return jsonify(dict(trip))
    else:
        return jsonify({'error': 'Trip not found'}), 404

# ==================== ZONES ENDPOINTS ====================

@app.route('/api/zones', methods=['GET'])
def get_zones():
    """Get all taxi zones"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    zones = cursor.execute('SELECT * FROM taxi_zones ORDER BY borough, zone').fetchall()
    zones_list = [dict(row) for row in zones]
    
    conn.close()
    return jsonify(zones_list)

@app.route('/api/zones/<int:location_id>', methods=['GET'])
def get_zone(location_id):
    """Get a specific zone with its boundary"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    zone = cursor.execute('SELECT * FROM taxi_zones WHERE location_id = ?', (location_id,)).fetchone()
    
    if not zone:
        conn.close()
        return jsonify({'error': 'Zone not found'}), 404
    
    zone_dict = dict(zone)
    
    # Get boundary if exists
    boundary = cursor.execute('SELECT geometry FROM zone_boundaries WHERE location_id = ?', (location_id,)).fetchone()
    if boundary:
        zone_dict['geometry'] = json.loads(boundary[0])
    
    conn.close()
    return jsonify(zone_dict)

@app.route('/api/zones/geojson', methods=['GET'])
def get_zones_geojson():
    """Get all zones as GeoJSON for mapping"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    zones = cursor.execute('''
        SELECT tz.*, zb.geometry
        FROM taxi_zones tz
        LEFT JOIN zone_boundaries zb ON tz.location_id = zb.location_id
    ''').fetchall()
    
    features = []
    for zone in zones:
        zone_dict = dict(zone)
        if zone_dict.get('geometry'):
            feature = {
                'type': 'Feature',
                'geometry': json.loads(zone_dict['geometry']),
                'properties': {
                    'location_id': zone_dict['location_id'],
                    'borough': zone_dict['borough'],
                    'zone': zone_dict['zone'],
                    'service_zone': zone_dict.get('service_zone')
                }
            }
            features.append(feature)
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    conn.close()
    return jsonify(geojson)

# ==================== ANALYTICS ENDPOINTS ====================

@app.route('/api/analytics/hourly', methods=['GET'])
def get_hourly_analytics():
    """Get trip statistics by hour of day"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    hourly_stats = cursor.execute('''
        SELECT 
            pickup_hour,
            COUNT(*) as trip_count,
            AVG(fare_amount) as avg_fare,
            AVG(trip_distance) as avg_distance,
            AVG(duration_min) as avg_duration,
            AVG(tip_pct) as avg_tip_pct,
            SUM(total_amount) as total_revenue
        FROM trips
        GROUP BY pickup_hour
        ORDER BY pickup_hour
    ''').fetchall()
    
    result = []
    for row in hourly_stats:
        result.append({
            'hour': row[0],
            'trip_count': row[1],
            'avg_fare': round(row[2], 2) if row[2] else 0,
            'avg_distance': round(row[3], 2) if row[3] else 0,
            'avg_duration': round(row[4], 2) if row[4] else 0,
            'avg_tip_pct': round(row[5], 2) if row[5] else 0,
            'total_revenue': round(row[6], 2) if row[6] else 0
        })
    
    conn.close()
    return jsonify(result)

@app.route('/api/analytics/by-borough', methods=['GET'])
def get_borough_analytics():
    """Get trip statistics by borough"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    borough_stats = cursor.execute('''
        SELECT 
            tz.borough,
            COUNT(*) as trip_count,
            AVG(t.fare_amount) as avg_fare,
            AVG(t.trip_distance) as avg_distance,
            AVG(t.duration_min) as avg_duration,
            SUM(t.total_amount) as total_revenue
        FROM trips t
        JOIN taxi_zones tz ON t.pickup_location_id = tz.location_id
        GROUP BY tz.borough
        ORDER BY trip_count DESC
    ''').fetchall()
    
    result = []
    for row in borough_stats:
        result.append({
            'borough': row[0],
            'trip_count': row[1],
            'avg_fare': round(row[2], 2) if row[2] else 0,
            'avg_distance': round(row[3], 2) if row[3] else 0,
            'avg_duration': round(row[4], 2) if row[4] else 0,
            'total_revenue': round(row[5], 2) if row[5] else 0
        })
    
    conn.close()
    return jsonify(result)

@app.route('/api/analytics/weekend-vs-weekday', methods=['GET'])
def get_weekend_comparison():
    """Compare weekend vs weekday statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    comparison = cursor.execute('''
        SELECT 
            is_weekend,
            COUNT(*) as trip_count,
            AVG(fare_amount) as avg_fare,
            AVG(trip_distance) as avg_distance,
            AVG(duration_min) as avg_duration,
            AVG(tip_pct) as avg_tip_pct
        FROM trips
        GROUP BY is_weekend
    ''').fetchall()
    
    result = {}
    for row in comparison:
        key = 'weekend' if row[0] == 1 else 'weekday'
        result[key] = {
            'trip_count': row[1],
            'avg_fare': round(row[2], 2) if row[2] else 0,
            'avg_distance': round(row[3], 2) if row[3] else 0,
            'avg_duration': round(row[4], 2) if row[4] else 0,
            'avg_tip_pct': round(row[5], 2) if row[5] else 0
        }
    
    conn.close()
    return jsonify(result)

@app.route('/api/analytics/top-routes', methods=['GET'])
def get_top_routes():
    """Get most popular pickup-dropoff routes"""
    limit = request.args.get('limit', 10, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    routes = cursor.execute('''
        SELECT 
            pz.borough as pickup_borough,
            pz.zone as pickup_zone,
            dz.borough as dropoff_borough,
            dz.zone as dropoff_zone,
            COUNT(*) as trip_count,
            AVG(t.fare_amount) as avg_fare,
            AVG(t.trip_distance) as avg_distance
        FROM trips t
        JOIN taxi_zones pz ON t.pickup_location_id = pz.location_id
        JOIN taxi_zones dz ON t.dropoff_location_id = dz.location_id
        GROUP BY t.pickup_location_id, t.dropoff_location_id
        ORDER BY trip_count DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    
    result = []
    for row in routes:
        result.append({
            'pickup_borough': row[0],
            'pickup_zone': row[1],
            'dropoff_borough': row[2],
            'dropoff_zone': row[3],
            'trip_count': row[4],
            'avg_fare': round(row[5], 2) if row[5] else 0,
            'avg_distance': round(row[6], 2) if row[6] else 0
        })
    
    conn.close()
    return jsonify(result)

@app.route('/api/analytics/fare-distribution', methods=['GET'])
def get_fare_distribution():
    """Get fare amount distribution in buckets"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    distribution = cursor.execute('''
        SELECT 
            CASE 
                WHEN fare_amount < 10 THEN '0-10'
                WHEN fare_amount < 20 THEN '10-20'
                WHEN fare_amount < 30 THEN '20-30'
                WHEN fare_amount < 50 THEN '30-50'
                ELSE '50+'
            END as fare_range,
            COUNT(*) as count
        FROM trips
        GROUP BY fare_range
        ORDER BY 
            CASE fare_range
                WHEN '0-10' THEN 1
                WHEN '10-20' THEN 2
                WHEN '20-30' THEN 3
                WHEN '30-50' THEN 4
                ELSE 5
            END
    ''').fetchall()
    
    result = [{'range': row[0], 'count': row[1]} for row in distribution]
    
    conn.close()
    return jsonify(result)

# ==================== MAIN ====================

if __name__ == '__main__':
    print("Starting NYC Taxi API Server...")
    print("API Documentation:")
    print("  - GET /api/health - Health check")
    print("  - GET /api/stats - Overall statistics")
    print("  - GET /api/trips - Get trips (with filters)")
    print("  - GET /api/trips/<id> - Get specific trip")
    print("  - GET /api/zones - Get all zones")
    print("  - GET /api/zones/<id> - Get specific zone")
    print("  - GET /api/zones/geojson - Get zones as GeoJSON")
    print("  - GET /api/analytics/hourly - Hourly statistics")
    print("  - GET /api/analytics/by-borough - Borough statistics")
    print("  - GET /api/analytics/weekend-vs-weekday - Weekend comparison")
    print("  - GET /api/analytics/top-routes - Most popular routes")
    print("  - GET /api/analytics/fare-distribution - Fare distribution")
    app.run(debug=True, port=5001, host='127.0.0.1')
