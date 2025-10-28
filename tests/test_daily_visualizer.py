from bot.reports.daily_visualizer import DailyVisualizer

def test_daily_visualizer():
    vis = DailyVisualizer()
    vis.generate_all()

if __name__ == "__main__":
    test_daily_visualizer()
