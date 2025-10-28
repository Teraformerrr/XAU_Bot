import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from loguru import logger

BASE = Path(__file__).resolve().parents[1] / "reports"
VISUALS = BASE / "visuals"
plt.rcParams["axes.grid"] = True


class PerformanceDashboard:
    def __init__(self):
        self.daily_path = BASE / "daily_summary.csv"
        self.metrics_path = BASE / "metrics_summary.json"
        logger.info("📊 Initializing Integrated Performance Dashboard")

    def load_daily_summary(self):
        if not self.daily_path.exists():
            logger.warning("⚠️ daily_summary.csv not found")
            return pd.DataFrame()
        df = pd.read_csv(self.daily_path)
        logger.info(f"📈 Loaded {len(df)} daily records")
        return df

    def load_metrics(self):
        if not self.metrics_path.exists():
            logger.warning("⚠️ metrics_summary.json not found")
            return {}
        with open(self.metrics_path, "r") as f:
            metrics = json.load(f)
        logger.info("📊 Metrics summary loaded")
        return metrics

    def display_summary(self, metrics):
        print("\n───────────── Portfolio Metrics ─────────────")
        for k, v in metrics.items():
            print(f"{k:20s}: {v}")
        print("────────────────────────────────────────────")

    def plot_all_visuals(self):
        visuals = [
            ("Equity Curve", VISUALS / "equity_curve.png"),
            ("PnL Trend", VISUALS / "pnl_trend.png"),
            ("Win-Rate Trend", VISUALS / "winrate_trend.png"),
        ]
        for title, path in visuals:
            if path.exists():
                img = plt.imread(path)
                plt.figure(figsize=(8, 4))
                plt.imshow(img)
                plt.axis("off")
                plt.title(title)
                plt.show()
                logger.info(f"✅ Displayed {title}")
            else:
                logger.warning(f"⚠️ Missing visual: {path.name}")

    def generate_html_report(self):
        html_file = BASE / "performance_dashboard.html"
        html = "<html><head><meta charset='UTF-8'><title>XAU_Bot Performance Dashboard</title></head><body>"
        html += "<h1 style='text-align:center'>📊 XAU_Bot Performance Dashboard</h1>"
        for img in VISUALS.glob("*.png"):
            html += f"<h3>{img.stem}</h3><img src='visuals/{img.name}' width='600'><br>"
        html += "</body></html>"
        # ✅ Write using UTF-8 encoding to avoid Windows emoji error
        html_file.write_text(html, encoding="utf-8")
        logger.info(f"🧾 HTML Dashboard generated → {html_file}")
        return html_file


def main():
    dash = PerformanceDashboard()
    daily = dash.load_daily_summary()
    metrics = dash.load_metrics()
    if not daily.empty:
        logger.info(f"Date range: {daily['date'].min()} → {daily['date'].max()}")
    dash.display_summary(metrics)
    dash.plot_all_visuals()
    dash.generate_html_report()
    logger.success("✅ Integrated Performance Dashboard completed.")


if __name__ == "__main__":
    main()
