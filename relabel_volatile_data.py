# TARGET_FILE: relabel_volatile_data.py
import pandas as pd
import numpy as np
import os

def relabel_volatile_data(input_path: str, output_path: str, look_ahead_seconds: int = 2):
    """
    Relabel dataset with volatility-adaptive thresholds.
    Robust to zero prices and edge cases.
    """
    print(f"Loading raw data from {input_path}")
    df = pd.read_csv(input_path)
    
    if len(df) < look_ahead_seconds + 20:
        print("Not enough data to label.")
        return

    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Remove invalid prices
    df = df[df['close'] > 0].copy()
    if len(df) < look_ahead_seconds + 20:
        print("Not enough valid price data after cleaning.")
        return
        
    df['label'] = np.nan
    
    # Calculate rolling volatility (std of returns over last 30s)
    df['returns'] = df['close'].pct_change()
    df['volatility_30s'] = df['returns'].rolling(window=30, min_periods=10).std()
    
    labeled_count = 0
    for i in range(len(df) - look_ahead_seconds):
        current_price = df.loc[i, 'close']
        future_price = df.loc[i + look_ahead_seconds, 'close']
        
        # Skip if prices are invalid
        if current_price <= 0 or future_price <= 0:
            continue
            
        change = (future_price - current_price) / current_price
        
        # Adaptive threshold: 1.5x recent volatility
        recent_vol = df.loc[i, 'volatility_30s']
        if pd.isna(recent_vol) or recent_vol == 0:
            threshold = 0.0005  # fallback
        else:
            threshold = max(0.0003, 1.5 * recent_vol)  # min 0.03%
        
        if change >= threshold:
            df.loc[i, 'label'] = 1  # buy
            labeled_count += 1
        elif change <= -threshold:
            df.loc[i, 'label'] = 0  # sell
            labeled_count += 1

    # Drop unlabeled rows
    labeled_df = df.dropna(subset=['label']).copy()
    if len(labeled_df) == 0:
        print("No samples met labeling criteria. Try lowering thresholds.")
        return
        
    labeled_df['label'] = labeled_df['label'].astype(int)
    
    # Save
    labeled_df.to_csv(output_path, index=False)
    print(f"Saved {len(labeled_df)} volatile-labeled samples to {output_path}")
    print(f"Class distribution:\n{labeled_df['label'].value_counts()}")
    avg_thresh = labeled_df['volatility_30s'].mean() * 1.5 if 'volatility_30s' in labeled_df else 0.0005
    print(f"Average adaptive threshold: {avg_thresh:.6f}")

if __name__ == "__main__":
    input_file = "datasets/btcusdt_volatile_1s_data.csv"
    output_file = "datasets/btcusdt_volatile_labeled.csv"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found! Run smart_data_collector.py first.")
    else:
        relabel_volatile_data(input_file, output_file)