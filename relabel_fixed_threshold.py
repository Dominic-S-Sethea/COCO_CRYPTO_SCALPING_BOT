# TARGET_FILE: relabel_fixed_threshold.py
import pandas as pd
import numpy as np
import os

def relabel_fixed_threshold(input_path: str, output_path: str, look_ahead_seconds: int = 2):
    print(f"Loading data from {input_path}")
    df = pd.read_csv(input_path)
    
    if len(df) < look_ahead_seconds + 10:
        print("Not enough data to label.")
        return

    df = df.sort_values('timestamp').reset_index(drop=True)
    df['label'] = np.nan
    
    labeled_count = 0
    for i in range(len(df) - look_ahead_seconds):
        current_price = df.loc[i, 'close']
        future_price = df.loc[i + look_ahead_seconds, 'close']
        
        if current_price <= 0 or future_price <= 0:
            continue
            
        change = (future_price - current_price) / current_price
        threshold = 0.0002  # Fixed 0.02% threshold
        
        if change >= threshold:
            df.loc[i, 'label'] = 1
            labeled_count += 1
        elif change <= -threshold:
            df.loc[i, 'label'] = 0
            labeled_count += 1

    labeled_df = df.dropna(subset=['label']).copy()
    if len(labeled_df) == 0:
        print("No samples met the 0.02% threshold. Try 0.01%.")
        return
        
    labeled_df['label'] = labeled_df['label'].astype(int)
    labeled_df.to_csv(output_path, index=False)
    print(f"Saved {len(labeled_df)} samples to {output_path}")
    print(f"Class distribution:\n{labeled_df['label'].value_counts()}")

if __name__ == "__main__":
    input_file = "datasets/btcusdt_volatile_labeled_input.csv"
    output_file = "datasets/btcusdt_volatile_labeled.csv"
    relabel_fixed_threshold(input_file, output_file)