from bot.scheduler.scheduler_main import Scheduler

def test_scheduler_cycle_report():
    sched = Scheduler(interval=1, mode="paper")
    sched.run_cycle()

if __name__ == "__main__":
    test_scheduler_cycle_report()
