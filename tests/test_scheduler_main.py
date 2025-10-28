import logging
from bot.scheduler.scheduler_main import SchedulerMain

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    s = SchedulerMain()
    s.run_cycle()  # single cycle test
