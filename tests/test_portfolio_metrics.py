from bot.portfolio.portfolio_metrics import PortfolioMetrics

if __name__ == "__main__":
    pm = PortfolioMetrics("portfolio.json")
    metrics = pm.summary()
    print("\nFinal Portfolio Metrics Summary:")
    for k, v in metrics.items():
        print(f"{k:<22}: {v}")
