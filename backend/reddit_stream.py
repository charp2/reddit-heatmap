"""
Reddit streaming module using PRAW.
Monitors specified subreddits for new posts and comments.
"""

import os
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Optional
from dataclasses import dataclass

import praw
from praw.models import Submission, Comment

from ticker_extractor import extract_tickers
from sentiment import analyze_sentiment


@dataclass
class RedditMention:
    """Represents a stock mention from Reddit."""
    ticker: str
    source: str  # subreddit
    content_type: str  # 'post' or 'comment'
    content: str
    sentiment: float
    author: str
    permalink: str
    created_at: datetime


# Default subreddits to monitor
DEFAULT_SUBREDDITS = ["wallstreetbets", "stocks", "options"]


def get_reddit_client() -> Optional[praw.Reddit]:
    """
    Create Reddit client using environment variables.

    Required env vars:
    - REDDIT_CLIENT_ID
    - REDDIT_CLIENT_SECRET
    - REDDIT_USER_AGENT (optional, defaults to 'RedditHeatmap/1.0')

    Returns:
        praw.Reddit instance or None if credentials missing
    """
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    user_agent = os.getenv("REDDIT_USER_AGENT", "RedditHeatmap/1.0")

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def has_reddit_credentials() -> bool:
    """Check if Reddit API credentials are configured."""
    return bool(os.getenv("REDDIT_CLIENT_ID") and os.getenv("REDDIT_CLIENT_SECRET"))


async def stream_submissions(
    subreddits: list[str] = None,
    on_mention: callable = None,
) -> AsyncGenerator[RedditMention, None]:
    """
    Stream new submissions from subreddits.

    Args:
        subreddits: List of subreddit names to monitor
        on_mention: Optional callback for each mention

    Yields:
        RedditMention objects for posts containing stock tickers
    """
    reddit = get_reddit_client()
    if not reddit:
        raise ValueError("Reddit credentials not configured")

    subreddits = subreddits or DEFAULT_SUBREDDITS
    subreddit_str = "+".join(subreddits)

    subreddit = reddit.subreddit(subreddit_str)

    # Use a thread executor since PRAW is synchronous
    loop = asyncio.get_event_loop()

    for submission in subreddit.stream.submissions(skip_existing=True):
        # Extract text content
        text = f"{submission.title} {submission.selftext}"
        tickers = extract_tickers(text)

        if not tickers:
            continue

        # Analyze sentiment
        sentiment_result = analyze_sentiment(text)

        # Create mention for each ticker found
        for ticker in tickers:
            mention = RedditMention(
                ticker=ticker,
                source=submission.subreddit.display_name,
                content_type="post",
                content=text[:500],
                sentiment=sentiment_result["compound"],
                author=str(submission.author) if submission.author else "[deleted]",
                permalink=f"https://reddit.com{submission.permalink}",
                created_at=datetime.fromtimestamp(submission.created_utc),
            )

            if on_mention:
                await on_mention(mention)

            yield mention

        # Small delay to be nice to Reddit API
        await asyncio.sleep(0.1)


async def stream_comments(
    subreddits: list[str] = None,
    on_mention: callable = None,
) -> AsyncGenerator[RedditMention, None]:
    """
    Stream new comments from subreddits.

    Args:
        subreddits: List of subreddit names to monitor
        on_mention: Optional callback for each mention

    Yields:
        RedditMention objects for comments containing stock tickers
    """
    reddit = get_reddit_client()
    if not reddit:
        raise ValueError("Reddit credentials not configured")

    subreddits = subreddits or DEFAULT_SUBREDDITS
    subreddit_str = "+".join(subreddits)

    subreddit = reddit.subreddit(subreddit_str)

    for comment in subreddit.stream.comments(skip_existing=True):
        tickers = extract_tickers(comment.body)

        if not tickers:
            continue

        # Analyze sentiment
        sentiment_result = analyze_sentiment(comment.body)

        # Create mention for each ticker found
        for ticker in tickers:
            mention = RedditMention(
                ticker=ticker,
                source=comment.subreddit.display_name,
                content_type="comment",
                content=comment.body[:500],
                sentiment=sentiment_result["compound"],
                author=str(comment.author) if comment.author else "[deleted]",
                permalink=f"https://reddit.com{comment.permalink}",
                created_at=datetime.fromtimestamp(comment.created_utc),
            )

            if on_mention:
                await on_mention(mention)

            yield mention

        await asyncio.sleep(0.1)


async def poll_new_posts(
    subreddits: list[str] = None,
    limit: int = 25,
    seen_ids: set = None,
) -> list[RedditMention]:
    """
    Poll for new posts (alternative to streaming).
    More reliable but slightly higher latency.

    Args:
        subreddits: List of subreddit names
        limit: Number of posts to fetch per subreddit
        seen_ids: Set of already-processed post IDs

    Returns:
        List of new RedditMention objects
    """
    reddit = get_reddit_client()
    if not reddit:
        return []

    subreddits = subreddits or DEFAULT_SUBREDDITS
    seen_ids = seen_ids or set()
    mentions = []

    for sub_name in subreddits:
        subreddit = reddit.subreddit(sub_name)

        for submission in subreddit.new(limit=limit):
            if submission.id in seen_ids:
                continue

            seen_ids.add(submission.id)

            text = f"{submission.title} {submission.selftext}"
            tickers = extract_tickers(text)

            if not tickers:
                continue

            sentiment_result = analyze_sentiment(text)

            for ticker in tickers:
                mentions.append(RedditMention(
                    ticker=ticker,
                    source=sub_name,
                    content_type="post",
                    content=text[:500],
                    sentiment=sentiment_result["compound"],
                    author=str(submission.author) if submission.author else "[deleted]",
                    permalink=f"https://reddit.com{submission.permalink}",
                    created_at=datetime.fromtimestamp(submission.created_utc),
                ))

    return mentions


if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()

    async def test():
        if not has_reddit_credentials():
            print("No Reddit credentials found. Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")
            return

        print("Starting Reddit stream test...")
        print("Monitoring: ", DEFAULT_SUBREDDITS)

        async def on_mention(mention):
            print(f"\n[{mention.ticker}] {mention.content_type} in r/{mention.source}")
            print(f"  Sentiment: {mention.sentiment:.2f}")
            print(f"  Content: {mention.content[:100]}...")

        # Test streaming (will run indefinitely)
        async for mention in stream_submissions(on_mention=on_mention):
            pass

    asyncio.run(test())
