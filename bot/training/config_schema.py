from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class LabelConfig:
    horizon_bars: int
    threshold_pct: float

@dataclass
class FeaturesConfig:
    include: List[str]
    normalize: bool = True

@dataclass
class SplitConfig:
    train_ratio: float
    val_ratio: float
    test_ratio: float
    shuffle: bool = False

@dataclass
class TrainerConfig:
    name: str
    params: Dict[str, Any]

@dataclass
class OutputConfig:
    model_dir: str
    artifacts_dir: str
    report_dir: str
    model_name: str

@dataclass
class TrainingConfig:
    data_path: str
    symbol: str
    timeframe: str
    label: LabelConfig
    features: FeaturesConfig
    split: SplitConfig
    trainer: TrainerConfig
    output: OutputConfig
