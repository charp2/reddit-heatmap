"""
Shared data models for Reddit Heatmap.
"""

from dataclasses import dataclass
from datetime import datetime


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
    score: int = 0  # Reddit score (upvotes - downvotes)
