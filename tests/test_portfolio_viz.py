# tests/test_portfolio_viz.py
from bot.visuals.portfolio_viz import PortfolioVisualizer

def test_portfolio_visualization():
    viz = PortfolioVisualizer(
        trade_log_path=r"D:\XAU_Bot\bot\data\trade_log.csv",
        output_dir=r"D:\XAU_Bot\reports"
    )

    viz.generate_all()

if __name__ == "__main__":
    test_portfolio_visualization()
