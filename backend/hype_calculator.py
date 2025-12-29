"""
Hype calculator with exponential decay.
Calculates "hype score" based on mention frequency with time decay.
"""

import math
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

# Decay half-life in seconds (10 minutes)
HALF_LIFE_SECONDS = 600
DECAY_LAMBDA = math.log(2) / HALF_LIFE_SECONDS

# Weight multipliers
POST_WEIGHT = 1.5  # Posts are worth more than comments
COMMENT_WEIGHT = 1.0


@dataclass
class MentionRecord:
    """Record of a single mention for hype calculation."""
    ticker: str
    timestamp: datetime
    content_type: str  # 'post' or 'comment'
    sentiment: float


@dataclass
class HypeScore:
    """Calculated hype score for a ticker."""
    ticker: str
    hype: float
    mention_count: int
    avg_sentiment: float
    velocity: float  # mentions per minute


class HypeCalculator:
    """
    Calculates and tracks hype scores for stock tickers.
    Uses exponential decay so recent mentions matter more.
    """

    def __init__(self, half_life_seconds: float = HALF_LIFE_SECONDS):
        self.mentions: list[MentionRecord] = []
        self.half_life = half_life_seconds
        self.decay_lambda = math.log(2) / half_life_seconds
        self._last_cleanup = datetime.now()

    def add_mention(
        self,
        ticker: str,
        content_type: str = "comment",
        sentiment: float = 0.0,
        timestamp: Optional[datetime] = None,
    ):
        """
        Add a new mention to the tracker.

        Args:
            ticker: Stock ticker symbol
            content_type: 'post' or 'comment'
            sentiment: Sentiment score (-1 to 1)
            timestamp: When the mention occurred (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        self.mentions.append(MentionRecord(
            ticker=ticker,
            timestamp=timestamp,
            content_type=content_type,
            sentiment=sentiment,
        ))

        # Periodic cleanup of old mentions
        if (datetime.now() - self._last_cleanup).total_seconds() > 300:
            self._cleanup_old_mentions()

    def _cleanup_old_mentions(self, max_age_minutes: int = 60):
        """Remove mentions older than max_age_minutes."""
        cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
        self.mentions = [m for m in self.mentions if m.timestamp > cutoff]
        self._last_cleanup = datetime.now()

    def _calculate_weight(self, mention: MentionRecord, now: datetime) -> float:
        """
        Calculate decayed weight for a single mention.

        Args:
            mention: The mention record
            now: Current timestamp

        Returns:
            Decayed weight value
        """
        # Time since mention in seconds
        age_seconds = (now - mention.timestamp).total_seconds()

        # Base weight based on content type
        base_weight = POST_WEIGHT if mention.content_type == "post" else COMMENT_WEIGHT

        # Apply exponential decay
        decay_factor = math.exp(-self.decay_lambda * age_seconds)

        return base_weight * decay_factor

    def get_hype_scores(self, top_n: int = 20) -> list[HypeScore]:
        """
        Calculate current hype scores for all tickers.

        Args:
            top_n: Number of top tickers to return

        Returns:
            List of HypeScore objects, sorted by hype descending
        """
        now = datetime.now()

        # Aggregate by ticker
        ticker_data: dict[str, dict] = defaultdict(lambda: {
            "total_weight": 0.0,
            "sentiment_sum": 0.0,
            "count": 0,
            "recent_count": 0,  # Last 5 minutes
        })

        five_min_ago = now - timedelta(minutes=5)

        for mention in self.mentions:
            weight = self._calculate_weight(mention, now)
            data = ticker_data[mention.ticker]

            data["total_weight"] += weight
            data["sentiment_sum"] += mention.sentiment
            data["count"] += 1

            if mention.timestamp > five_min_ago:
                data["recent_count"] += 1

        # Build HypeScore objects
        scores = []
        for ticker, data in ticker_data.items():
            if data["count"] == 0:
                continue

            scores.append(HypeScore(
                ticker=ticker,
                hype=round(data["total_weight"], 2),
                mention_count=data["count"],
                avg_sentiment=round(data["sentiment_sum"] / data["count"], 3),
                velocity=round(data["recent_count"] / 5.0, 2),  # per minute
            ))

        # Sort by hype score descending
        scores.sort(key=lambda x: x.hype, reverse=True)

        return scores[:top_n]

    def get_ticker_hype(self, ticker: str) -> Optional[HypeScore]:
        """
        Get hype score for a specific ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            HypeScore or None if no mentions
        """
        now = datetime.now()
        five_min_ago = now - timedelta(minutes=5)

        total_weight = 0.0
        sentiment_sum = 0.0
        count = 0
        recent_count = 0

        for mention in self.mentions:
            if mention.ticker != ticker:
                continue

            weight = self._calculate_weight(mention, now)
            total_weight += weight
            sentiment_sum += mention.sentiment
            count += 1

            if mention.timestamp > five_min_ago:
                recent_count += 1

        if count == 0:
            return None

        return HypeScore(
            ticker=ticker,
            hype=round(total_weight, 2),
            mention_count=count,
            avg_sentiment=round(sentiment_sum / count, 3),
            velocity=round(recent_count / 5.0, 2),
        )

    def get_stats(self) -> dict:
        """
        Get overall statistics.

        Returns:
            Dict with total mentions, unique tickers, etc.
        """
        now = datetime.now()
        five_min_ago = now - timedelta(minutes=5)
        one_hour_ago = now - timedelta(hours=1)

        recent_mentions = [m for m in self.mentions if m.timestamp > five_min_ago]
        hourly_mentions = [m for m in self.mentions if m.timestamp > one_hour_ago]

        unique_tickers = set(m.ticker for m in self.mentions)

        return {
            "total_mentions": len(self.mentions),
            "unique_tickers": len(unique_tickers),
            "mentions_last_5min": len(recent_mentions),
            "mentions_last_hour": len(hourly_mentions),
            "velocity": round(len(recent_mentions) / 5.0, 2),  # per minute
        }


# Global calculator instance
_calculator = HypeCalculator()


def get_calculator() -> HypeCalculator:
    """Get the global hype calculator instance."""
    return _calculator


if __name__ == "__main__":
    import random

    # Test the calculator
    calc = HypeCalculator()

    # Add some test mentions with varying timestamps
    tickers = ["TSLA", "NVDA", "GME", "AMD", "AAPL"]
    now = datetime.now()

    for i in range(100):
        ticker = random.choice(tickers)
        # Random time in last 30 minutes
        timestamp = now - timedelta(minutes=random.uniform(0, 30))
        content_type = "post" if random.random() < 0.3 else "comment"
        sentiment = random.uniform(-0.5, 0.8)

        calc.add_mention(ticker, content_type, sentiment, timestamp)

    # Get results
    print("Top Hype Scores:")
    print("-" * 60)
    for score in calc.get_hype_scores(10):
        print(f"{score.ticker:6} | Hype: {score.hype:6.2f} | "
              f"Count: {score.mention_count:3} | "
              f"Sentiment: {score.avg_sentiment:+.2f} | "
              f"Velocity: {score.velocity:.1f}/min")

    print("\nOverall Stats:")
    print(calc.get_stats())
