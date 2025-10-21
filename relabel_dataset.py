import pandas as pd
import numpy as np
import os

def relabel_scalping_data(input_path: str, output_path: str, look_ahead_seconds: int = 3, threshold_pct: float = 0.08):
    """
    Add labels to raw feature dataset based on future price movement.
    """
    print(f"Loading raw data from {input_path}")
    df = pd.read_csv(input_path)
    
    if len(df) < look_ahead_seconds + 10:
        print("Not enough data to label.")
        return

    df = df.sort_values('timestamp').reset_index(drop=True)
    df['label'] = np.nan
    threshold = threshold_pct / 100.0
    
    for i in range(len(df) - look_ahead_seconds):
        current_price = df.loc[i, 'close']
        future_price = df.loc[i + look_ahead_seconds, 'close']
        if current_price <= 0:
            continue
        change = (future_price - current_price) / current_price
        
        if change >= threshold:
            df.loc[i, 'label'] = 1
        elif change <= -threshold:
            df.loc[i, 'label'] = 0
    
    labeled_df = df.dropna(subset=['label']).copy()
    labeled_df['label'] = labeled_df['label'].astype(int)
    labeled_df.to_csv(output_path, index=False)
    print(f"Saved {len(labeled_df)} labeled samples to {output_path}")
    print(f"Class distribution:\n{labeled_df['label'].value_counts()}") 

if __name__ == "__main__":
    input_file = "datasets/btcusdt_1s_scalping_data.csv"
    output_file = "datasets/btcusdt_1s_labeled.csv"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found!")
    else:
        relabel_scalping_data(
            input_path=input_file,
            output_path=output_file,
            look_ahead_seconds=2,      # ↓ Look ahead only 2 seconds
            threshold_pct=0.03         # ↓ Require only 0.03% move
        )