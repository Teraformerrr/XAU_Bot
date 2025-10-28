# D:\XAU_Bot\bot\core\scheduler.py
import time
from bot.core.session_logger import SessionLogger

class ContinuousScheduler:
    def __init__(self, task_fn, interval_sec=300):
        self.task_fn = task_fn
        self.interval_sec = interval_sec
        self.logger = SessionLogger()
        self.running = True

    def start(self):
        self.logger.log_event("SCHEDULER_START", f"🕒 Interval: {self.interval_sec}s")
        try:
            while self.running:
                cycle_start = time.time()
                self.logger.log_event("CYCLE_START", "🔁 New cycle triggered")
                try:
                    self.task_fn()
                    self.logger.log_event("CYCLE_END", "✅ Cycle completed successfully")
                except Exception as e:
                    self.logger.log_event("ERROR", str(e))
                time.sleep(max(0, self.interval_sec - (time.time() - cycle_start)))
        except KeyboardInterrupt:
            self.logger.log_event("INTERRUPT", "🛑 Stopped by user")
        finally:
            self.logger.close()
