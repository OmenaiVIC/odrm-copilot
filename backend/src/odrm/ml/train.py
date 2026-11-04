import datetime
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import RandomizedSearchCV

from odrm.ml.features import build_feature_frame, extract_target, TARGETS, FEATURES
from odrm.ml.dataset import prepare_dataset
from odrm.ml.gates import evaluate_gates
from odrm.ml.registry import save_model

def get_git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("ascii").strip()
    except Exception:
        return "unknown"

def train_single_target(df: pd.DataFrame, target: str, model_root: Path, random_state: int = 7) -> dict:
    """Trains, evaluates, gates, and saves a model for a single target."""
    
    # 1. Prepare Data
    train_df, test_df = prepare_dataset(df, test_size=0.2, random_state=random_state)
    X_train = build_feature_frame(train_df)
    y_train = extract_target(train_df, target)
    X_test = build_feature_frame(test_df)
    y_test = extract_target(test_df, target)

    # 2. Setup Model
    base_model = xgb.XGBRegressor(
        objective="reg:squarederror",
        tree_method="hist",
        random_state=random_state,
        n_jobs=2 
    )
    
    # Full search space from SPRINT_2_PLAN.md §3.4
    param_grid = {
        "n_estimators": [200, 400, 600],
        "max_depth": [3, 4, 5, 6, 8],
        "learning_rate": [0.03, 0.05, 0.1, 0.2],
        "subsample": [0.7, 0.85, 1.0],
        "colsample_bytree": [0.7, 0.85, 1.0],
        "min_child_weight": [1, 3, 5],
    }
    
    search = RandomizedSearchCV(
        base_model,
        param_distributions=param_grid,
        n_iter=15, # Increased for better tuning
        scoring="neg_root_mean_squared_error",
        cv=3, # 3-fold is standard and safe
        random_state=random_state,
        n_jobs=1
    )
    
    search.fit(X_train, y_train)
    best_model = search.best_estimator_

    # 3. Evaluate
    train_preds = best_model.predict(X_train)
    test_preds = best_model.predict(X_test)
    
    # Calculate metrics
    test_mse = mean_squared_error(y_test, test_preds)
    test_rmse = np.sqrt(test_mse)
    test_mae = mean_absolute_error(y_test, test_preds)
    
    metrics = {
        "train_r2": float(r2_score(y_train, train_preds)),
        "test_r2": float(r2_score(y_test, test_preds)),
        "test_rmse": float(test_rmse),
        "test_mae": float(test_mae)
    }
    
    # 4. Gate
    gate_metrics = {target: {"r2": metrics["test_r2"], "rmse": metrics["test_rmse"]}}
    evaluate_gates(gate_metrics)

    # 5. Save via Registry
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    version = f"v1-{timestamp}"
    
    metadata = {
        "schema_version": "v1",
        "target": target,
        "model_version": version,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "features": list(FEATURES),
        "hyperparameters": search.best_params_,
        "metrics": metrics,
        "git_sha": get_git_sha(),
    }
    
    save_model(best_model, metadata, root=model_root)
    return metadata