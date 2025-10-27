import os
import json
import subprocess
from pathlib import Path

def test_training_pipeline_runs():
    root = Path(__file__).resolve().parents[1]
    # Run the pipeline as a module
    proc = subprocess.run(
        ["python", "-m", "bot.training.pipeline"],
        cwd=root,
        capture_output=True,
        text=True
    )
    print(proc.stdout)
    print(proc.stderr)
    assert proc.returncode == 0, f"Pipeline failed: {proc.stderr}"

    # Check outputs
    model_dir = root / "models" / "xgb"
    report_dir = root / "reports" / "training"
    artifacts_dir = root / "artifacts"

    assert model_dir.exists()
    assert any(p.suffix in [".bin", ".joblib"] for p in model_dir.iterdir())
    assert (report_dir / "training_summary.json").exists()
    assert (artifacts_dir / "scaler.joblib").exists()
    assert (artifacts_dir / "features.json").exists()
    assert (artifacts_dir / "labels_map.json").exists()
