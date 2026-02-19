import pandas as pd
import os


def link_metadata(trips_df, lookup_df):
    # Merge for Pickup Locations
    merged = trips_df.merge(
        lookup_df,
        left_on='PULocationID',
        right_on='LocationID',
        how='left'
    )
    merged.rename(columns={'Borough': 'pickup_borough', 'Zone': 'pickup_zone'}, inplace=True)

    # Merge for Dropoff Locations
    merged = merged.merge(
        lookup_df,
        left_on='DOLocationID',
        right_on='LocationID',
        how='left'
    )
    merged.rename(columns={'Borough': 'dropoff_borough', 'Zone': 'dropoff_zone'}, inplace=True)
    
    return merged



def engineer_features(df):

    df['tpep_pickup_datetime'] = pd.to_datetime(df['tpep_pickup_datetime'])
    df['tpep_dropoff_datetime'] = pd.to_datetime(df['tpep_dropoff_datetime'])

    # Core Features
    df['duration_min'] = (df['tpep_dropoff_datetime'] - df['tpep_pickup_datetime']).dt.total_seconds() / 60
    df['fare_per_mile'] = df['fare_amount'] / df['trip_distance'].replace(0, 1)
    df['pickup_hour'] = df['tpep_pickup_datetime'].dt.hour
    
    # Custom Extended Features
    df['pickup_dayofweek'] = df['tpep_pickup_datetime'].dt.dayofweek
    df['is_weekend'] = df['pickup_dayofweek'].isin([5, 6]).astype(int)
    
    # Speed Calculation (Miles per hour)
    df['speed_mph'] = df['trip_distance'] / (df['duration_min'] / 60).replace(0, 1)
    
    # Tip Percentage & Efficiency
    df['tip_pct'] = (df['tip_amount'] / df['fare_amount'] * 100).fillna(0).round(1)
    df['fare_per_min'] = (df['fare_amount'] / df['duration_min'].replace(0, 1)).round(2)
    
    return df


def main():
    # Setup paths
    trip_file = 'yellow_tripdata_2019-01.csv'
    lookup_file = 'taxi_zone_lookup.csv'
    output_file = 'processed_mobility_data.csv'

    # Clear old results
    if os.path.exists(output_file):
        os.remove(output_file)

    print("--- Starting Full Integration Pipeline ---")

    try:
        # Load metadata once
        zone_lookup = pd.read_csv(lookup_file)
        
        # CHUNKING: Processes the full rows in segments to save RAM
        chunk_size = 200000 
        first_chunk = True
        total_rows = 0

        for chunk in pd.read_csv(trip_file, chunksize=chunk_size):
            # Apply your logic
            integrated = link_metadata(chunk, zone_lookup)
            final = engineer_features(integrated)
            
            # Save to CSV (Append mode)
            final.to_csv(output_file, mode='a', index=False, header=first_chunk)
            
            total_rows += len(final)
            print(f"Current Progress: {total_rows} rows processed...")
            first_chunk = False

        print(f"\nDONE! {total_rows} records integrated and saved to {output_file}.")

    except FileNotFoundError:
        print("ERROR: Could not find 'yellow_tripdata.csv' or 'taxi_zone_lookup.csv'.")
    except Exception as e:
        print(f"AN UNEXPECTED ERROR OCCURRED: {e}")

if __name__ == "__main__":
    main()
