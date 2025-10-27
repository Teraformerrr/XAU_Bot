import json
import joblib
import numpy as np
from pathlib import Path
from typing import Dict
from sklearn.metrics import classification_report, accuracy_score, f1_score
from xgboost import XGBClassifier

from .registry import register_trainer

@register_trainer("xgb_classifier")
def train_xgb(
    X_train, y_train, X_val, y_val, X_test, y_test,
    params: Dict, save_dir: str, model_name: str
):
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    clf = XGBClassifier(**params)
    clf.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    # Evaluate
    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    f1m = f1_score(y_test, preds, average="macro")

    report = classification_report(y_test, preds, output_dict=True)
    metrics = {
        "accuracy": float(acc),
        "f1_macro": float(f1m),
        "report": report
    }

    # Save model and metrics
    model_file = save_path / model_name
    joblib.dump(clf, model_file)

    metrics_file = save_path / "metrics.json"
    metrics_file.write_text(json.dumps(metrics, indent=2))

    return {
        "model_path": str(model_file),
        "metrics_path": str(metrics_file),
        "metrics": metrics
    }
