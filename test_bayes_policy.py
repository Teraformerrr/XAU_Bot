# D:\XAU_Bot\test_bayes_policy.py
from bot.engines.bayes_policy import BayesianPolicy

if __name__ == "__main__":
    policy = BayesianPolicy()
    sample_cases = [
        {"conf": 0.60, "vol": 0.05, "drift": False},
        {"conf": 0.42, "vol": 0.20, "drift": True},
        {"conf": 0.50, "vol": 0.10, "drift": False}
    ]
    for case in sample_cases:
        result = policy.decide(**case)
        print(result)
