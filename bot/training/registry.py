from typing import Dict, Callable

_REGISTRY: Dict[str, Callable] = {}

def register_trainer(name: str):
    def deco(fn: Callable):
        _REGISTRY[name] = fn
        return fn
    return deco

def get_trainer(name: str) -> Callable:
    if name not in _REGISTRY:
        raise KeyError(f"Trainer '{name}' not found. Registered: {list(_REGISTRY)}")
    return _REGISTRY[name]
