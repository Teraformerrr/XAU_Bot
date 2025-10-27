import os
from pathlib import Path

def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)

def join_root(*parts):
    return str(Path().resolve().joinpath(*parts))
