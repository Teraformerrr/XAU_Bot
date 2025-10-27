import json
import yaml
import joblib
import numpy as np
from pathlib import Path
from dataclasses import asdict
from sklearn.utils.class_weight import compute_class_weight

# registers xgb_classifier
from bot.training import trainer_xgb  

from .config_schema import TrainingConfig, LabelConfig, FeaturesConfig, SplitConfig, TrainerConfig, OutputConfig
from .data_loader import DataLoader
from .feature_engineer import FeatureEngineer
from .labeler import Labeler, LABELS_MAP
from .splits import time_series_split, drop_tail
from .registry import get_trainer
from .utils import ensure_dir


def _load_training_config(cfg: dict) -> TrainingConfig:
    t = cfg["training"]
    return TrainingConfig(
        data_path=t["data_path"],
        symbol=t["symbol"],
        timeframe=t["timeframe"],
        label=LabelConfig(**t["label"]),
        features=FeaturesConfig(**t["features"]),
        split=SplitConfig(**t["split"]),
        trainer=TrainerConfig(**t["trainer"]),
        output=OutputConfig(**t["output"])
    )

def main():
    # 1) Load config
    cfg_path = Path("config.yaml")
    if not cfg_path.exists():
        raise FileNotFoundError("config.yaml not found in project root.")
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    tcfg = _load_training_config(cfg)

    # 2) Prepare dirs
    ensure_dir(tcfg.output.model_dir)
    ensure_dir(tcfg.output.artifacts_dir)
    ensure_dir(tcfg.output.report_dir)

    # 3) Load data
    df = DataLoader(tcfg.data_path).load()

    # 4) Labels
    labeler = Labeler(tcfg.label.horizon_bars, tcfg.label.threshold_pct)
    y_full = labeler.make_labels(df)

    # 5) Features (fit scaler on full train split only later)
    feat = FeatureEngineer(tcfg.features.include, normalize=tcfg.features.normalize)

    # 6) Drop the last h rows (no future label)
    h = int(tcfg.label.horizon_bars)
    df_valid = df.iloc[:-h].copy()
    y = y_full[:-h]

    # 7) Split by time
    n = len(df_valid)
    tr, va, te = time_series_split(n, tcfg.split.train_ratio, tcfg.split.val_ratio)

    # 8) Build matrices with proper fit/transform
    X_all, _ = feat.build_matrix(df_valid, fit=True)
    X_train, y_train = X_all[tr], y[tr]
    X_val,   y_val   = X_all[va], y[va]
    X_test,  y_test  = X_all[te], y[te]

    # 9) Save artifacts (scaler + label mapping + feature list)
    import json
    import joblib
    artifacts_dir = Path(tcfg.output.artifacts_dir)
    joblib.dump(feat.scaler, artifacts_dir / "scaler.joblib")
    (artifacts_dir / "labels_map.json").write_text(json.dumps({k:int(v) for k,v in LABELS_MAP.items()}, indent=2))
    (artifacts_dir / "features.json").write_text(json.dumps(tcfg.features.include, indent=2))
    (artifacts_dir / "training_config.snapshot.json").write_text(json.dumps(cfg["training"], indent=2))

    # 10) Handle class imbalance (optional): weights info only
    classes = np.unique(y_train)
    class_weights = compute_class_weight(class_weight="balanced", classes=classes, y=y_train)
    weights_info = {int(c): float(w) for c, w in zip(classes, class_weights)}
    (artifacts_dir / "class_weights.json").write_text(json.dumps(weights_info, indent=2))

    # 11) Shift negative labels to positive integers
    if y_train.min() < 0:
        y_train = y_train + 1
        y_val = y_val + 1
        y_test = y_test + 1


    # 11) Train using registry
    trainer_fn = get_trainer(tcfg.trainer.name)
    result = trainer_fn(
        X_train, y_train, X_val, y_val, X_test, y_test,
        params=tcfg.trainer.params,
        save_dir=tcfg.output.model_dir,
        model_name=tcfg.output.model_name
    )

    # 12) Save a compact summary in report dir
    report_dir = Path(tcfg.output.report_dir)
    summary = {
        "symbol": tcfg.symbol,
        "timeframe": tcfg.timeframe,
        "data_path": tcfg.data_path,
        "samples": {"train": len(X_train), "val": len(X_val), "test": len(X_test)},
        "features": tcfg.features.include,
        "label_horizon_bars": tcfg.label.horizon_bars,
        "label_threshold_pct": tcfg.label.threshold_pct,
        "trainer": tcfg.trainer.name,
        "metrics": result["metrics"],
        "model_path": result["model_path"]
    }
    (report_dir / "training_summary.json").write_text(json.dumps(summary, indent=2))

    print("✅ Training complete.")
    print(f"📦 Model: {result['model_path']}")
    print(f"🧪 Metrics: {result['metrics_path']}")
    print(f"📝 Report: {report_dir / 'training_summary.json'}")

if __name__ == "__main__":
    main()
