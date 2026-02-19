import pandas as pd
import os

def clean_mobility_data(input_file, output_file, log_file):
    print(f"--- Cleaning Started: {input_file} ---")
    
    if not os.path.exists(input_file):
        print("Error: Input file not found.")
        return

    # 1. Load data
    df = pd.read_csv(input_file)
    initial_count = len(df)
    
    # DROP TECHNICAL CLUTTER (Service zones and duplicate IDs)
    garbage_cols = ['service_zone_x', 'service_zone_y', 'LocationID_x', 'LocationID_y']
    df.drop(columns=[c for c in garbage_cols if c in df.columns], inplace=True, errors='ignore')
    
    # Clean infine values
    df.replace([float('inf'), -float('inf')], 0, inplace=True)

    # Dropoff must be after pickup
    df = df[df['tpep_dropoff_datetime'] > df['tpep_pickup_datetime']]

    # Passenger count checks
    if 'passenger_count' in df.columns:
        df = df[df['passenger_count'] >= 0]
    
    # Tip amount check
    if 'tip_amount' in df.columns:
        df = df[df['tip_amount'] >= 0]
    
    # Removing rows with impossible values
    clean_df = df[
        (df['trip_distance'] > 0) & 
        (df['fare_amount'] > 0) & 
        (df['duration_min'] > 0) &
        (df['speed_mph'] < 100) &
        (df['speed_mph'] > 1) 
    ].copy()
    
    # 4. FINAL STANDARDIZATION
    clean_df.drop_duplicates(inplace=True)
    clean_df.dropna(subset=['pickup_borough', 'dropoff_borough'], inplace=True)
    
    # 5. GENERATE LOG file
    final_count = len(clean_df)
    with open(log_file, 'w') as f:
        f.write(f"Initial Records: {initial_count}\n")
        f.write(f"Cleaned Records: {final_count}\n")
        f.write(f"Removed: {initial_count - final_count}\n")
    
    # 6. SAVE
    clean_df.to_csv(output_file, index=False)
    
    # Summary Print
    print(f"DONE: Removed {initial_count - final_count} anomalies.")
    print(f"Final file: {output_file} ({final_count} records)")

if __name__ == "__main__":
    clean_mobility_data('processed_mobility_data.csv', 'final_cleaned_data.csv', 'cleaning_log.txt')
