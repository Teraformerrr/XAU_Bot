# D:\XAU_Bot\bot\utils\prob.py
from __future__ import annotations
import math

EPS = 1e-12

def clip01(x: float) -> float:
    if x < EPS: return EPS
    if x > 1.0 - EPS: return 1.0 - EPS
    return x

def logit(p: float) -> float:
    p = clip01(p)
    return math.log(p / (1.0 - p))

def sigmoid(x: float) -> float:
    # numerically stable
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)
