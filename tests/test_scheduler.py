from bot.core.scheduler import ContinuousScheduler

def simple_task():
    print("Running test cycle...")

if __name__ == "__main__":
    scheduler = ContinuousScheduler(task_fn=simple_task, interval_sec=10)
    scheduler.start()
