from bot.reports.daily_aggregator import DailyAggregator

def test_daily_aggregator():
    agg = DailyAggregator()
    summary = agg.aggregate()
    if summary:
        print("✅ Daily summary aggregation complete:")
        for date, stats in summary.items():
            print(f"{date} → {stats}")
    else:
        print("⚠️ No cycle summaries found.")

if __name__ == "__main__":
    test_daily_aggregator()
