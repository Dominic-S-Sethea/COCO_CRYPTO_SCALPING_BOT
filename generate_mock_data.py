import numpy as np
import pandas as pd
import os

def generate_mock_scalping_data(output_path: str, n_samples: int = 2000):
    np.random.seed(42)
    
    # Simulate realistic 1s features
    price_change_1s = np.random.normal(0, 0.0005, n_samples)
    price_change_5s = np.random.normal(0, 0.001, n_samples)
    volatility_10s = np.random.exponential(0.0008, n_samples)
    volume_10s = np.random.exponential(10.0, n_samples)
    price_acceleration = np.random.normal(0, 0.0001, n_samples)

    # Create labels based on future move
    labels = []
    for i in range(n_samples):
        if price_change_5s[i] > 0.0008:
            labels.append(1)
        elif price_change_5s[i] < -0.0008:
            labels.append(0)
        else:
            labels.append(np.nan)

    # Fake timestamp and price
    timestamps = np.arange(1700000000000, 1700000000000 + n_samples * 1000, 1000)
    base_price = 60000.0
    price_noise = np.random.normal(0, 5, n_samples)
    close_prices = base_price + np.cumsum(price_noise)

    df = pd.DataFrame({
        'timestamp': timestamps[:len(labels)],
        'close': close_prices[:len(labels)],
        'price_change_1s': price_change_1s[:len(labels)],
        'price_change_5s': price_change_5s[:len(labels)],
        'volatility_10s': volatility_10s[:len(labels)],
        'volume_10s': volume_10s[:len(labels)],
        'price_acceleration': price_acceleration[:len(labels)],
        'label': labels
    })
    
    # Remove neutral samples
    df = df.dropna(subset=['label']).reset_index(drop=True)
    df['label'] = df['label'].astype(int)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"✅ Generated {len(df)} mock labeled samples to {output_path}")
    print(f"Class distribution:\n{df['label'].value_counts()}")

if __name__ == "__main__":
    generate_mock_scalping_data("datasets/btcusdt_1s_labeled.csv", n_samples=2000)