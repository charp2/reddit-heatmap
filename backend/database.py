"""
SQLite database module for storing stock mentions.
Uses aiosqlite for async operations.
"""

import aiosqlite
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "mentions.db"


async def init_db():
    """Initialize the database and create tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                source TEXT NOT NULL,
                content_type TEXT NOT NULL,
                content TEXT,
                sentiment REAL,
                author TEXT,
                permalink TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for efficient queries
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticker_time
            ON mentions(ticker, created_at)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at
            ON mentions(created_at)
        """)

        await db.commit()


async def add_mention(
    ticker: str,
    source: str,
    content_type: str,
    content: Optional[str] = None,
    sentiment: Optional[float] = None,
    author: Optional[str] = None,
    permalink: Optional[str] = None,
) -> int:
    """
    Add a new mention to the database.

    Args:
        ticker: Stock ticker symbol
        source: Subreddit name
        content_type: 'post' or 'comment'
        content: Text content (truncated)
        sentiment: Compound sentiment score
        author: Reddit username
        permalink: Link to post/comment

    Returns:
        ID of inserted row
    """
    # Truncate content to save space
    if content and len(content) > 500:
        content = content[:500] + "..."

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO mentions (ticker, source, content_type, content, sentiment, author, permalink)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ticker, source, content_type, content, sentiment, author, permalink)
        )
        await db.commit()
        return cursor.lastrowid


async def get_mentions_since(
    since: datetime,
    ticker: Optional[str] = None,
) -> list[dict]:
    """
    Get all mentions since a given timestamp.

    Args:
        since: Start timestamp
        ticker: Optional filter by ticker

    Returns:
        List of mention dicts
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if ticker:
            cursor = await db.execute(
                """
                SELECT * FROM mentions
                WHERE created_at >= ? AND ticker = ?
                ORDER BY created_at DESC
                """,
                (since.isoformat(), ticker)
            )
        else:
            cursor = await db.execute(
                """
                SELECT * FROM mentions
                WHERE created_at >= ?
                ORDER BY created_at DESC
                """,
                (since.isoformat(),)
            )

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_ticker_stats(since: datetime) -> list[dict]:
    """
    Get aggregated stats per ticker since a timestamp.

    Args:
        since: Start timestamp

    Returns:
        List of dicts with ticker, count, avg_sentiment
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                ticker,
                COUNT(*) as mention_count,
                AVG(sentiment) as avg_sentiment,
                SUM(CASE WHEN content_type = 'post' THEN 1 ELSE 0 END) as post_count,
                SUM(CASE WHEN content_type = 'comment' THEN 1 ELSE 0 END) as comment_count
            FROM mentions
            WHERE created_at >= ?
            GROUP BY ticker
            ORDER BY mention_count DESC
            """,
            (since.isoformat(),)
        )

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_recent_mentions(limit: int = 50) -> list[dict]:
    """
    Get most recent mentions.

    Args:
        limit: Max number of mentions to return

    Returns:
        List of mention dicts
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT * FROM mentions
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        )

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def cleanup_old_mentions(days: int = 7):
    """
    Remove mentions older than specified days.

    Args:
        days: Age threshold for deletion
    """
    cutoff = datetime.now() - timedelta(days=days)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM mentions WHERE created_at < ?",
            (cutoff.isoformat(),)
        )
        await db.commit()


if __name__ == "__main__":
    import asyncio

    async def test():
        await init_db()

        # Add test mentions
        await add_mention(
            ticker="TSLA",
            source="wallstreetbets",
            content_type="post",
            content="TSLA to the moon!",
            sentiment=0.8,
            author="test_user",
        )

        await add_mention(
            ticker="GME",
            source="wallstreetbets",
            content_type="comment",
            content="Diamond hands! 💎🙌",
            sentiment=0.6,
        )

        # Query
        since = datetime.now() - timedelta(hours=1)
        mentions = await get_mentions_since(since)
        print(f"Mentions in last hour: {len(mentions)}")

        stats = await get_ticker_stats(since)
        print(f"Ticker stats: {stats}")

        recent = await get_recent_mentions(10)
        print(f"Recent mentions: {len(recent)}")

    asyncio.run(test())
