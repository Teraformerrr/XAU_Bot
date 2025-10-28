import logging
from bot.engines.adaptive_feedback import AdaptiveFeedback

# Configure logging for direct console output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if __name__ == "__main__":
    af = AdaptiveFeedback()
    af.update("XAUUSD.sd", win=True, conf=0.78)
    af.update("XAUUSD.sd", win=False, conf=0.65)
