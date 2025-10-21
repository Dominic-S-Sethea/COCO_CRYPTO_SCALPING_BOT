# TARGET_FILE: strategies/scalping_features.py
import numpy as np
from typing import List, Dict, Optional

def compute_scalping_features(klines: List[Dict]) -> Optional[np.ndarray]:
    """
    Compute vectorized features from last N 1s klines.
    Returns shape (5,) array or None if insufficient data.
    """
    if len(klines) < 10:
        return None

    closes = np.array([k['c'] for k in klines], dtype=np.float32)
    volumes = np.array([k['v'] for k in klines], dtype=np.float32)

    # Price changes
    price_change_1s = (closes[-1] - closes[-2]) / closes[-2]
    price_change_5s = (closes[-1] - closes[-6]) / closes[-6]

    # Volatility (std of returns over last 10s)
    returns = np.diff(closes) / closes[:-1]
    volatility_10s = np.std(returns[-10:]) if len(returns) >= 10 else 0.0

    # Volume sum last 10s
    volume_10s = np.sum(volumes[-10:])

    # Price acceleration (2nd derivative approx)
    if len(closes) >= 3:
        vel1 = closes[-1] - closes[-2]
        vel2 = closes[-2] - closes[-3]
        price_acceleration = vel1 - vel2
    else:
        price_acceleration = 0.0

    features = np.array([
        price_change_1s,
        price_change_5s,
        volatility_10s,
        volume_10s,
        price_acceleration
    ], dtype=np.float32)

    return features