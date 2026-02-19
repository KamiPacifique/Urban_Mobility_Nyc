import time
from typing import List, Dict, Any, Optional
from database import get_db_connection


# ==================== HASH TABLE ====================

class CustomHashTable:
    """
    Hash Table with separate chaining
    Time: Insert/Search - O(1) average | Space: O(n)
    """
    
    def __init__(self, size: int = 256):
        self.size = size
        self.buckets = [[] for _ in range(size)]
    
    def _hash(self, key: Any) -> int:
        return hash(key) % self.size
    
    def insert(self, key: Any, value: Any) -> None:
        """O(1) average"""
        index = self._hash(key)
        bucket = self.buckets[index]
        
        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        bucket.append((key, value))
    
    def get(self, key: Any) -> Optional[Any]:
        """O(1) average"""
        index = self._hash(key)
        for k, v in self.buckets[index]:
            if k == key:
                return v
        return None


# ==================== MERGE SORT ====================

def merge_sort(items: List[Dict], key: str = 'fare_amount', reverse: bool = False) -> List[Dict]:
    """
    Merge Sort - Divide and Conquer
    
    Pseudo-code:
    ------------
    FUNCTION MergeSort(array, key):
        IF length <= 1: RETURN array
        mid = length / 2
        left = MergeSort(array[0:mid])
        right = MergeSort(array[mid:end])
        RETURN Merge(left, right)
    
    Time: O(n log n) | Space: O(n) | Stable: Yes
    """
    if len(items) <= 1:
        return items
    
    mid = len(items) // 2
    left = merge_sort(items[:mid], key, reverse)
    right = merge_sort(items[mid:], key, reverse)
    
    # Merge
    result, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        condition = left[i].get(key, 0) >= right[j].get(key, 0) if reverse else left[i].get(key, 0) <= right[j].get(key, 0)
        if condition:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    
    result.extend(left[i:])
    result.extend(right[j:])
    return result


# ==================== BINARY SEARCH ====================

def binary_search(items: List[Dict], target_id: int) -> Optional[Dict]:
    """
    Binary Search (requires sorted array)
    
    Pseudo-code:
    ------------
    FUNCTION BinarySearch(array, target):
        low = 0, high = length - 1
        WHILE low <= high:
            mid = (low + high) / 2
            IF array[mid] == target: RETURN array[mid]
            ELSE IF array[mid] < target: low = mid + 1
            ELSE: high = mid - 1
        RETURN None
    
    Time: O(log n) | Space: O(1)
    """
    low, high = 0, len(items) - 1
    
    while low <= high:
        mid = (low + high) // 2
        mid_id = items[mid].get('location_id', -1)
        
        if mid_id == target_id:
            return items[mid]
        elif mid_id < target_id:
            low = mid + 1
        else:
            high = mid - 1
    return None


# ==================== GROUP BY ====================

def group_by_aggregate(items: List[Dict], group_key: str, agg_key: str, func: str = 'sum') -> Dict:
    """
    Manual GROUP BY aggregation
    Time: O(n) | Space: O(n)
    """
    groups = {}
    for item in items:
        key = item.get(group_key)
        if key not in groups:
            groups[key] = []
        groups[key].append(item.get(agg_key, 0))
    
    result = {}
    for key, values in groups.items():
        if func == 'sum':
            result[key] = sum(values)
        elif func == 'avg':
            result[key] = sum(values) / len(values) if values else 0
        elif func == 'count':
            result[key] = len(values)
    return result


# ==================== DEMONSTRATION ====================

def demonstrate_algorithms():
    """Demonstrate algorithms with real taxi data"""
    print("=" * 70)
    print("NYC TAXI - CUSTOM ALGORITHM DEMONSTRATION")
    print("=" * 70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Load sample data
    print("\n Loading sample data...")
    trips = cursor.execute('''
        SELECT t.fare_amount, t.trip_distance, 
               pz.borough as pickup_borough, pz.zone as pickup_zone,
               t.pickup_location_id
        FROM trips t
        LEFT JOIN taxi_zones pz ON t.pickup_location_id = pz.location_id
        LIMIT 1000
    ''').fetchall()
    trips_list = [dict(row) for row in trips]
    
    zones = cursor.execute('SELECT * FROM taxi_zones').fetchall()
    zones_list = [dict(row) for row in zones]
    print(f" Loaded {len(trips_list)} trips, {len(zones_list)} zones\n")
    
    # 1. Hash Table
    print("1. HASH TABLE - Zone Lookup (O(1) average)")
    print("-" * 70)
    start = time.time()
    ht = CustomHashTable()
    for z in zones_list:
        ht.insert(z['location_id'], z)
    
    result = ht.get(161)
    print(f"Inserted {len(zones_list)} zones in {time.time()-start:.4f}s")
    print(f"Lookup Zone 161: {result['zone']}, {result['borough']}\n")
    
    # 2. Merge Sort
    print("2. MERGE SORT - Top Fares (O(n log n))")
    print("-" * 70)
    start = time.time()
    sorted_trips = merge_sort(trips_list[:500], 'fare_amount', reverse=True)
    print(f"Sorted 500 trips in {time.time()-start:.4f}s")
    print("Top 3 fares:")
    for i, t in enumerate(sorted_trips[:3], 1):
        print(f"  {i}. ${t['fare_amount']:.2f} - {t.get('pickup_zone', 'Unknown')}")
    
    # 3. Binary Search
    print("\n3. BINARY SEARCH - Find Zone (O(log n))")
    print("-" * 70)
    sorted_zones = merge_sort(zones_list, 'location_id')
    for zone_id in [132, 161, 237]:
        result = binary_search(sorted_zones, zone_id)
        if result:
            print(f"  Zone {zone_id}: {result['zone']}")
    
    # 4. Group By
    print("\n4. GROUP BY AGGREGATION (O(n))")
    print("-" * 70)
    start = time.time()
    totals = group_by_aggregate(trips_list, 'pickup_borough', 'fare_amount', 'sum')
    print(f"Aggregated in {time.time()-start:.4f}s")
    for borough, total in sorted(totals.items(), key=lambda x: x[1], reverse=True)[:3]:
        if borough:
            print(f"  {borough}: ${total:,.2f}")
    
    conn.close()
    print("\n" + "=" * 70)
    print(" All algorithms manually implemented without built-in functions")
    print("=" * 70)


if __name__ == "__main__":
    demonstrate_algorithms()
