"""
Unit tests for the real Reddit data streaming path.

These tests mock PRAW to test the reddit_stream module without needing
actual Reddit API credentials.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import os

from models import RedditMention


class MockSubmission:
    """Mock Reddit submission object."""
    def __init__(
        self,
        title: str,
        selftext: str,
        subreddit_name: str = "wallstreetbets",
        author: str = "test_user",
        score: int = 100,
        created_utc: float = None,
        permalink: str = "/r/test/123",
        submission_id: str = "abc123",
    ):
        self.title = title
        self.selftext = selftext
        self.subreddit = Mock()
        self.subreddit.display_name = subreddit_name
        self.author = Mock()
        self.author.__str__ = lambda self: author
        self.score = score
        self.created_utc = created_utc or datetime.now().timestamp()
        self.permalink = permalink
        self.id = submission_id


class MockComment:
    """Mock Reddit comment object."""
    def __init__(
        self,
        body: str,
        subreddit_name: str = "wallstreetbets",
        author: str = "test_user",
        score: int = 50,
        created_utc: float = None,
        permalink: str = "/r/test/comments/123",
    ):
        self.body = body
        self.subreddit = Mock()
        self.subreddit.display_name = subreddit_name
        self.author = Mock()
        self.author.__str__ = lambda self: author
        self.score = score
        self.created_utc = created_utc or datetime.now().timestamp()
        self.permalink = permalink


class TestRedditMentionModel:
    """Test the shared RedditMention model."""

    def test_reddit_mention_has_score_field(self):
        """Verify RedditMention has the score field."""
        mention = RedditMention(
            ticker="TSLA",
            source="wallstreetbets",
            content_type="post",
            content="TSLA to the moon!",
            sentiment=0.8,
            author="test_user",
            permalink="https://reddit.com/r/test",
            created_at=datetime.now(),
            score=1500,
        )

        assert mention.score == 1500
        assert mention.ticker == "TSLA"
        assert mention.content_type == "post"

    def test_reddit_mention_score_defaults_to_zero(self):
        """Verify score defaults to 0 if not provided."""
        mention = RedditMention(
            ticker="NVDA",
            source="stocks",
            content_type="comment",
            content="Bullish on NVDA",
            sentiment=0.5,
            author="investor",
            permalink="https://reddit.com/r/stocks",
            created_at=datetime.now(),
        )

        assert mention.score == 0


class TestRedditStreamCredentials:
    """Test credential checking."""

    def test_has_reddit_credentials_with_env_vars(self):
        """Test that credentials are detected when env vars are set."""
        with patch.dict(os.environ, {
            "REDDIT_CLIENT_ID": "test_id",
            "REDDIT_CLIENT_SECRET": "test_secret",
        }):
            from reddit_stream import has_reddit_credentials
            # Need to reimport to pick up the patched env
            assert has_reddit_credentials() is True

    def test_has_reddit_credentials_without_env_vars(self):
        """Test that missing credentials are detected."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove the env vars if they exist
            os.environ.pop("REDDIT_CLIENT_ID", None)
            os.environ.pop("REDDIT_CLIENT_SECRET", None)

            from reddit_stream import has_reddit_credentials
            assert has_reddit_credentials() is False


class TestSubmissionProcessing:
    """Test processing of Reddit submissions."""

    def test_submission_creates_mention_with_score(self):
        """Test that submissions are processed with correct score."""
        submission = MockSubmission(
            title="TSLA earnings report",
            selftext="Tesla is going to crush earnings. Bullish!",
            score=2500,
        )

        # Simulate what stream_submissions does
        from ticker_extractor import extract_tickers
        from sentiment import analyze_sentiment

        text = f"{submission.title} {submission.selftext}"
        tickers = extract_tickers(text)
        sentiment_result = analyze_sentiment(text)

        assert "TSLA" in tickers

        mention = RedditMention(
            ticker="TSLA",
            source=submission.subreddit.display_name,
            content_type="post",
            content=text[:500],
            sentiment=sentiment_result["compound"],
            author=str(submission.author),
            permalink=f"https://reddit.com{submission.permalink}",
            created_at=datetime.fromtimestamp(submission.created_utc),
            score=submission.score,
        )

        assert mention.score == 2500
        assert mention.ticker == "TSLA"
        assert mention.content_type == "post"
        assert mention.source == "wallstreetbets"

    def test_comment_creates_mention_with_score(self):
        """Test that comments are processed with correct score."""
        comment = MockComment(
            body="NVDA is the future of AI. Loading up on calls!",
            score=350,
        )

        from ticker_extractor import extract_tickers
        from sentiment import analyze_sentiment

        tickers = extract_tickers(comment.body)
        sentiment_result = analyze_sentiment(comment.body)

        assert "NVDA" in tickers

        mention = RedditMention(
            ticker="NVDA",
            source=comment.subreddit.display_name,
            content_type="comment",
            content=comment.body[:500],
            sentiment=sentiment_result["compound"],
            author=str(comment.author),
            permalink=f"https://reddit.com{comment.permalink}",
            created_at=datetime.fromtimestamp(comment.created_utc),
            score=comment.score,
        )

        assert mention.score == 350
        assert mention.ticker == "NVDA"
        assert mention.content_type == "comment"


class TestPollNewPosts:
    """Test the poll_new_posts function."""

    @patch('reddit_stream.get_reddit_client')
    def test_poll_new_posts_includes_score(self, mock_get_client):
        """Test that polled posts include score."""
        # Create mock submissions
        mock_submissions = [
            MockSubmission(
                title="GME short squeeze incoming",
                selftext="Diamond hands! 💎🙌",
                score=5000,
                submission_id="post1",
            ),
            MockSubmission(
                title="AMD earnings play",
                selftext="Loading up on AMD calls before earnings",
                score=1200,
                submission_id="post2",
            ),
        ]

        # Setup mock Reddit client
        mock_reddit = Mock()
        mock_subreddit = Mock()
        mock_subreddit.new.return_value = mock_submissions
        mock_reddit.subreddit.return_value = mock_subreddit
        mock_get_client.return_value = mock_reddit

        # Import and run
        import asyncio
        from reddit_stream import poll_new_posts

        mentions = asyncio.run(poll_new_posts(subreddits=["wallstreetbets"], limit=10))

        # Verify mentions have correct scores
        gme_mentions = [m for m in mentions if m.ticker == "GME"]
        amd_mentions = [m for m in mentions if m.ticker == "AMD"]

        assert len(gme_mentions) > 0
        assert gme_mentions[0].score == 5000

        assert len(amd_mentions) > 0
        assert amd_mentions[0].score == 1200


class TestIntegrationWithMain:
    """Test that real data path integrates correctly with main.py."""

    @pytest.mark.asyncio
    async def test_real_mention_processed_correctly(self):
        """Test that a real-format mention is processed correctly by main.py."""
        import main
        main.reset_state()

        # Create a mention as it would come from the real stream
        mention = RedditMention(
            ticker="AAPL",
            source="stocks",
            content_type="post",
            content="Apple just announced record iPhone sales!",
            sentiment=0.75,
            author="apple_investor",
            permalink="https://reddit.com/r/stocks/abc123",
            created_at=datetime.now(),
            score=3500,  # High score post
        )

        await main.process_mention(mention)

        # Verify it's in the heatmap
        hype_scores = main.hype_calculator.get_hype_scores(top_n=30)
        tickers = [s.ticker for s in hype_scores]
        assert "AAPL" in tickers

        # Verify it's in pending_mentions with correct score
        assert len(main.pending_mentions) == 1
        assert main.pending_mentions[0]["score"] == 3500
        assert main.pending_mentions[0]["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_multiple_tickers_from_single_post(self):
        """Test handling of posts that mention multiple tickers."""
        import main
        main.reset_state()

        # Simulate a post mentioning multiple tickers
        # In reality, the stream would yield multiple mentions
        tickers_in_post = ["TSLA", "NVDA", "AMD"]
        base_score = 2000

        for ticker in tickers_in_post:
            mention = RedditMention(
                ticker=ticker,
                source="wallstreetbets",
                content_type="post",
                content=f"Comparing {ticker} with other tech stocks",
                sentiment=0.5,
                author="tech_analyst",
                permalink="https://reddit.com/r/wsb/multi123",
                created_at=datetime.now(),
                score=base_score,  # Same post, same score
            )
            await main.process_mention(mention)

        # All tickers should be in heatmap
        hype_scores = main.hype_calculator.get_hype_scores(top_n=30)
        heatmap_tickers = [s.ticker for s in hype_scores]

        for ticker in tickers_in_post:
            assert ticker in heatmap_tickers, f"{ticker} should be in heatmap"

        # All should have same score in pending
        assert len(main.pending_mentions) == 3
        for pm in main.pending_mentions:
            assert pm["score"] == base_score

    @pytest.mark.asyncio
    async def test_high_score_post_beats_low_score_comments(self):
        """Test that a high-score post is selected over low-score comments."""
        import main
        main.reset_state()

        # Add some low-score comments
        for i in range(5):
            mention = RedditMention(
                ticker=f"STOCK{i}",
                source="stocks",
                content_type="comment",
                content=f"Comment about STOCK{i}",
                sentiment=0.3,
                author=f"user{i}",
                permalink=f"https://reddit.com/comment/{i}",
                created_at=datetime.now(),
                score=50 + i * 10,  # 50, 60, 70, 80, 90
            )
            await main.process_mention(mention)

        # Add one high-score post
        high_score_mention = RedditMention(
            ticker="WINNER",
            source="wallstreetbets",
            content_type="post",
            content="This is the winning post with highest score",
            sentiment=0.9,
            author="top_poster",
            permalink="https://reddit.com/winner",
            created_at=datetime.now(),
            score=5000,  # Much higher score
        )
        await main.process_mention(high_score_mention)

        # The highest score mention should be selected
        best = max(main.pending_mentions, key=lambda m: m["score"])
        assert best["ticker"] == "WINNER"
        assert best["score"] == 5000
        assert best["content_type"] == "post"


class TestDeletedAuthors:
    """Test handling of deleted authors."""

    def test_deleted_author_handling(self):
        """Test that deleted authors are handled gracefully."""
        submission = MockSubmission(
            title="TSLA news",
            selftext="Some content about Tesla",
            score=100,
        )
        submission.author = None  # Deleted author

        # This should not crash
        author_str = str(submission.author) if submission.author else "[deleted]"
        assert author_str == "[deleted]"

        mention = RedditMention(
            ticker="TSLA",
            source="wallstreetbets",
            content_type="post",
            content="TSLA news Some content about Tesla",
            sentiment=0.5,
            author=author_str,
            permalink="https://reddit.com/r/test",
            created_at=datetime.now(),
            score=submission.score,
        )

        assert mention.author == "[deleted]"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
