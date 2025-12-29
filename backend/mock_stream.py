"""
Mock data stream for demo mode.
Generates realistic WSB-style posts when Reddit API credentials are not available.
"""

import asyncio
import random
from datetime import datetime
from typing import AsyncGenerator, Callable, Optional
from dataclasses import dataclass

from ticker_extractor import extract_tickers
from sentiment import analyze_sentiment


@dataclass
class RedditMention:
    """Represents a stock mention from Reddit."""
    ticker: str
    source: str
    content_type: str
    content: str
    sentiment: float
    author: str
    permalink: str
    created_at: datetime


# Weighted ticker list (more popular = higher weight)
WEIGHTED_TICKERS = [
    ("TSLA", 15),
    ("NVDA", 14),
    ("GME", 12),
    ("AMD", 10),
    ("AAPL", 10),
    ("MSFT", 8),
    ("META", 8),
    ("AMZN", 7),
    ("GOOGL", 6),
    ("SPY", 6),
    ("QQQ", 5),
    ("AMC", 5),
    ("PLTR", 5),
    ("COIN", 4),
    ("SOFI", 4),
    ("RIVN", 3),
    ("NIO", 3),
    ("INTC", 3),
    ("BA", 3),
    ("DIS", 2),
    ("NFLX", 2),
    ("PYPL", 2),
    ("SQ", 2),
    ("SHOP", 2),
    ("CRWD", 2),
    ("SNOW", 2),
    ("UBER", 2),
    ("HOOD", 2),
]

# Build weighted selection list
TICKER_POOL = []
for ticker, weight in WEIGHTED_TICKERS:
    TICKER_POOL.extend([ticker] * weight)

# Mock subreddits
SUBREDDITS = ["wallstreetbets", "stocks", "options"]

# Mock usernames
USERNAMES = [
    "diamond_hands_dave", "yolo_trader", "tendies_hunter", "smooth_brain_steve",
    "ape_strong", "wsb_autist", "call_me_maybe", "puts_printer", "theta_gang_tom",
    "moon_shot_mike", "bag_holder_bob", "fomo_fred", "paper_hands_pete",
    "leverage_larry", "options_wizard", "degen_trader", "stonks_only_go_up",
    "buy_high_sell_low", "wife_boyfriend", "wendy_worker", "casino_royale",
]

# Template categories
BULLISH_TEMPLATES = [
    "{ticker} to the moon! 🚀🚀🚀",
    "Just loaded up on {ticker} calls. LFG!",
    "{ticker} is going to squeeze so hard, diamond hands only 💎🙌",
    "Why is nobody talking about {ticker}? This thing is about to rip",
    "Bought 100 shares of {ticker}, am I doing this right?",
    "YOLO'd my entire portfolio into {ticker} calls expiring Friday",
    "{ticker} breaking out! Get in before it's too late",
    "Trust me bro, {ticker} is the play. Easy 10 bagger",
    "My wife's boyfriend told me to buy {ticker}. All in!",
    "{ticker} earnings next week, loading up on calls",
    "Just saw some unusual options activity on {ticker} 👀",
    "{ticker} short interest is insane. Squeeze incoming",
    "DD on {ticker}: This is literally free money",
    "Apes, {ticker} needs our help! Buy and hold! 🦍",
    "{ticker} dip is a gift. Buying more here",
]

BEARISH_TEMPLATES = [
    "{ticker} is overvalued garbage. Puts printing 🐻",
    "Why is {ticker} still this high? Loading puts",
    "{ticker} earnings will be a disaster. Short it",
    "Just sold all my {ticker}. This thing is done",
    "{ticker} bag holders in shambles 😂",
    "Bought {ticker} puts. Thanks for the free money bulls",
    "{ticker} is going to zero. Change my mind",
    "Lost everything on {ticker} calls. I belong here",
    "{ticker} rug pull incoming. You've been warned",
    "Paper handed my {ticker} position. No regrets",
]

NEUTRAL_TEMPLATES = [
    "What's everyone's thoughts on {ticker}?",
    "Should I buy {ticker} at this price or wait for a dip?",
    "Anyone holding {ticker} through earnings?",
    "{ticker} chart looking interesting. What do you see?",
    "Need some DD on {ticker}. Is it a buy?",
    "Sold covered calls on {ticker}. Theta gang rise up",
    "What's the PT on {ticker}? Analysts seem split",
    "{ticker} IV is insane right now",
    "Playing {ticker} earnings with a straddle",
    "Entry point for {ticker}? Waiting for a pullback",
]

ENTITY_TEMPLATES = [
    "Elon just tweeted again. {ticker} about to move",
    "Did you see what Jensen said at GTC? {ticker} is the future",
    "Tim Cook presenting new products. {ticker} calls it is",
    "Zuck going all in on AI. {ticker} to the moon",
    "Ryan Cohen tweeted a poop emoji. You know what that means 🚀",
    "Satya Nadella killing it. {ticker} looking strong",
    "Jeff Bezos buying more {ticker}. Insider knows best",
    "Lisa Su delivering again. {ticker} gang eating good",
]

# Entity to ticker mapping for templates
ENTITY_TICKERS = {
    "Elon": "TSLA",
    "Jensen": "NVDA",
    "Tim Cook": "AAPL",
    "Zuck": "META",
    "Ryan Cohen": "GME",
    "Satya Nadella": "MSFT",
    "Jeff Bezos": "AMZN",
    "Lisa Su": "AMD",
}


def generate_mock_post() -> tuple[str, str, float]:
    """
    Generate a random mock Reddit post.

    Returns:
        Tuple of (ticker, content, expected_sentiment)
    """
    # Decide sentiment category
    sentiment_roll = random.random()

    if sentiment_roll < 0.5:
        # 50% bullish
        templates = BULLISH_TEMPLATES
        expected_sentiment = random.uniform(0.3, 0.9)
    elif sentiment_roll < 0.75:
        # 25% bearish
        templates = BEARISH_TEMPLATES
        expected_sentiment = random.uniform(-0.9, -0.3)
    else:
        # 25% neutral
        templates = NEUTRAL_TEMPLATES
        expected_sentiment = random.uniform(-0.2, 0.2)

    # Occasionally use entity-based templates
    if random.random() < 0.15:
        template = random.choice(ENTITY_TEMPLATES)
        # Find which ticker this template maps to
        for entity, ticker in ENTITY_TICKERS.items():
            if entity in template:
                return ticker, template.format(ticker=ticker), random.uniform(0.2, 0.8)

    ticker = random.choice(TICKER_POOL)
    content = random.choice(templates).format(ticker=ticker)

    # Sometimes add emoji spam for extra WSB flavor
    if random.random() < 0.3:
        emojis = random.choice(["🚀", "💎🙌", "🦍", "📈", "🐻", "🔥", "💰", "🎰"])
        content += f" {emojis * random.randint(1, 3)}"

    return ticker, content, expected_sentiment


async def stream_mock_mentions(
    interval_range: tuple[float, float] = (1.0, 4.0),
    on_mention: Optional[Callable] = None,
) -> AsyncGenerator[RedditMention, None]:
    """
    Stream mock Reddit mentions at random intervals.

    Args:
        interval_range: Min and max seconds between posts
        on_mention: Optional callback for each mention

    Yields:
        RedditMention objects
    """
    post_id = 1000

    while True:
        ticker, content, _ = generate_mock_post()

        # Get actual sentiment from analyzer
        sentiment_result = analyze_sentiment(content)

        # Decide if post or comment
        content_type = "post" if random.random() < 0.3 else "comment"

        mention = RedditMention(
            ticker=ticker,
            source=random.choice(SUBREDDITS),
            content_type=content_type,
            content=content,
            sentiment=sentiment_result["compound"],
            author=random.choice(USERNAMES),
            permalink=f"https://reddit.com/r/wallstreetbets/comments/mock{post_id}",
            created_at=datetime.now(),
        )

        post_id += 1

        if on_mention:
            await on_mention(mention)

        yield mention

        # Random delay between posts
        delay = random.uniform(*interval_range)
        await asyncio.sleep(delay)


async def generate_initial_data(count: int = 50) -> list[RedditMention]:
    """
    Generate initial batch of mock data for immediate display.

    Args:
        count: Number of mentions to generate

    Returns:
        List of RedditMention objects
    """
    mentions = []
    post_id = 1

    for _ in range(count):
        ticker, content, _ = generate_mock_post()
        sentiment_result = analyze_sentiment(content)

        mention = RedditMention(
            ticker=ticker,
            source=random.choice(SUBREDDITS),
            content_type="post" if random.random() < 0.3 else "comment",
            content=content,
            sentiment=sentiment_result["compound"],
            author=random.choice(USERNAMES),
            permalink=f"https://reddit.com/r/wallstreetbets/comments/init{post_id}",
            created_at=datetime.now(),
        )

        mentions.append(mention)
        post_id += 1

    return mentions


if __name__ == "__main__":
    async def test():
        print("Testing mock stream...")
        print("=" * 50)

        async def on_mention(mention):
            print(f"\n[{mention.ticker}] {mention.content_type} in r/{mention.source}")
            print(f"  Author: u/{mention.author}")
            print(f"  Sentiment: {mention.sentiment:.2f}")
            print(f"  Content: {mention.content}")

        count = 0
        async for mention in stream_mock_mentions(interval_range=(0.5, 1.5), on_mention=on_mention):
            count += 1
            if count >= 10:
                break

        print("\n" + "=" * 50)
        print("Mock stream test complete!")

    asyncio.run(test())
