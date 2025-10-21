# TARGET_FILE: train_scalping_model.py
import pandas as pd
import xgboost as xgb
import numpy as np
import os
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

def train_scalping_model(data_path: str, model_save_path: str):
    print(f"Loading labeled data from {data_path}")
    df = pd.read_csv(data_path)
    
    if len(df) < 100:
        print("Not enough labeled data (<100 samples). Collect more first.")
        return

    feature_cols = [
        'price_change_1s',
        'price_change_5s',
        'volatility_10s',
        'volume_10s',
        'price_acceleration'
    ]
    
    X = df[feature_cols].values
    y = df['label'].values
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Training on {len(X_train)} samples, testing on {len(X_test)}")
    
    # Train XGBoost classifier
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nTest Accuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Sell', 'Buy']))
    
    # Save model
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    model.save_model(model_save_path)
    print(f"\n✅ Model saved to: {model_save_path}")
    
    # Save feature importance
    importance = dict(zip(feature_cols, model.feature_importances_.tolist()))
    with open(model_save_path.replace('.json', '_features.json'), 'w') as f:
        json.dump(importance, f, indent=2)
    print(f"Feature importance saved.")

if __name__ == "__main__":
    labeled_data = "datasets/btcusdt_volatile_labeled.csv"  # ✅ Updated for volatile data
    model_path = "models/scalping_model.json"
    
    if not os.path.exists(labeled_data):
        print(f"Error: {labeled_data} not found. Run relabel_volatile_data.py first.")
    else:
        train_scalping_model(labeled_data, model_path)