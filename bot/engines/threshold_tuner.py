import json
import logging
from pathlib import Path
from datetime import datetime

class ThresholdTuner:
    def __init__(self, bayes_state_path="bayes_state.json", feedback_path="reports/feedback_log.jsonl"):
        self.bayes_state_path = Path(bayes_state_path)
        self.feedback_path = Path(feedback_path)
        self.base_buy = 0.555
        self.base_sell = 0.445
        self.load_bayes()
        self.logger = logging.getLogger(__name__)

    def load_bayes(self):
        if self.bayes_state_path.exists():
            with open(self.bayes_state_path, "r") as f:
                self.bayes_state = json.load(f)
        else:
            self.bayes_state = {}

    def recent_feedback_stats(self, window=30):
        """Compute win ratio and avg confidence from recent feedback"""
        wins, losses, confs = 0, 0, []
        if not self.feedback_path.exists():
            return 0.5, 0.0  # default neutral

        with open(self.feedback_path, "r") as f:
            lines = f.readlines()[-window:]
            for line in lines:
                try:
                    rec = json.loads(line)
                    confs.append(rec.get("confidence", 0.5))
                    if rec.get("win", False):
                        wins += 1
                    else:
                        losses += 1
                except:
                    continue

        total = wins + losses
        win_rate = wins / total if total > 0 else 0.5
        avg_conf = sum(confs) / len(confs) if confs else 0.5
        return win_rate, avg_conf

    def tune(self):
        win_rate, avg_conf = self.recent_feedback_stats()
        delta = (win_rate - 0.5) * 0.1  # adjust strength
        adj_buy = self.base_buy + delta
        adj_sell = self.base_sell - delta
        adj_buy = max(min(adj_buy, 0.65), 0.50)
        adj_sell = max(min(adj_sell, 0.50), 0.35)
        tuned = {
            "timestamp": datetime.utcnow().isoformat(),
            "win_rate": round(win_rate, 3),
            "avg_conf": round(avg_conf, 3),
            "buy_th": round(adj_buy, 3),
            "sell_th": round(adj_sell, 3),
        }

        Path("reports").mkdir(exist_ok=True)
        with open("reports/thresholds.json", "w") as f:
            json.dump(tuned, f, indent=2)

        self.logger.info(f"🎯 Thresholds tuned → {tuned}")
        return tuned
