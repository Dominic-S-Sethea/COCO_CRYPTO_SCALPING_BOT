# TARGET_FILE: strategies/scalping_model.py
import os
import numpy as np
import xgboost as xgb
import logging

logger = logging.getLogger("ScalpingModel")

def load_scalping_model(model_path: str):
    """Load XGBoost model if exists, else return None."""
    if os.path.exists(model_path):
        try:
            model = xgb.Booster()
            model.load_model(model_path)
            logger.info(f"Loaded scalping model from {model_path}")
            return model
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
    else:
        logger.warning(f"Model not found at {model_path}. Place trained model there to enable trading.")
    return None

def predict_signal(model, features: np.ndarray) -> tuple:
    """
    Returns (confidence: float, side: str) where side is 'buy' or 'sell'.
    If model is None, returns (0.0, 'neutral').
    """
    if model is None or features is None:
        return 0.0, 'neutral'

    dmat = xgb.DMatrix(features.reshape(1, -1))
    pred = model.predict(dmat)[0]  # Assume output: 0=sell, 1=buy

    if pred > 0.6:
        return float(pred), 'buy'
    elif pred < 0.4:
        return float(1 - pred), 'sell'
    else:
        return 0.0, 'neutral'

# Placeholder training script (run separately)
def train_placeholder_model():
    """
    Run this once you have collected labeled 1s data.
    Save to models/scalping_model.json
    """
    import os
    os.makedirs("models", exist_ok=True)
    print("Placeholder: Train your model and save to models/scalping_model.json")
    print("Expected features (in order):")
    print("- price_change_1s")
    print("- price_change_5s")
    print("- volatility_10s")
    print("- volume_10s")
    print("- price_acceleration")
    print("Label: 1 for buy, 0 for sell (based on next 2s price move)")