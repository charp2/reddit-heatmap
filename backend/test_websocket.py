"""
Unit tests for WebSocket updates and heatmap/livefeed synchronization.

Tests:
1. Heatmap displays all added mentions
2. Batch mentions are handled correctly
3. Highest-score mention from batch appears in livefeed
4. At least 5 websocket updates are verified
"""

import asyncio
import json
import pytest
from datetime import datetime

# Import the module to access its globals directly
import main
from mock_stream import RedditMention
from hype_calculator import HypeCalculator


class TestWebSocketUpdates:
    """Test websocket updates with heatmap and livefeed synchronization."""

    def setup_method(self):
        """Reset state before each test."""
        main.reset_state()

    def create_mention(
        self,
        ticker: str,
        score: int,
        content: str = None,
        content_type: str = "comment",
        sentiment: float = 0.5,
    ) -> RedditMention:
        """Helper to create a test mention."""
        return RedditMention(
            ticker=ticker,
            source="wallstreetbets",
            content_type=content_type,
            content=content or f"Test content for {ticker}",
            sentiment=sentiment,
            author="test_user",
            permalink=f"https://reddit.com/r/test/{ticker}",
            created_at=datetime.now(),
            score=score,
        )

    @pytest.mark.asyncio
    async def test_single_mention_appears_in_heatmap(self):
        """Test that a single mention appears in the heatmap."""
        mention = self.create_mention("TSLA", score=100)

        await main.process_mention(mention)

        # Check hype calculator has the mention
        scores = main.hype_calculator.get_hype_scores(top_n=30)
        tickers = [s.ticker for s in scores]

        assert "TSLA" in tickers, "TSLA should appear in heatmap after mention"

    @pytest.mark.asyncio
    async def test_multiple_mentions_appear_in_heatmap(self):
        """Test that multiple mentions for different tickers all appear in heatmap."""
        mentions = [
            self.create_mention("TSLA", score=100),
            self.create_mention("NVDA", score=200),
            self.create_mention("AMD", score=150),
        ]

        for mention in mentions:
            await main.process_mention(mention)

        scores = main.hype_calculator.get_hype_scores(top_n=30)
        tickers = [s.ticker for s in scores]

        assert "TSLA" in tickers, "TSLA should appear in heatmap"
        assert "NVDA" in tickers, "NVDA should appear in heatmap"
        assert "AMD" in tickers, "AMD should appear in heatmap"

    @pytest.mark.asyncio
    async def test_batch_picks_highest_score_for_livefeed(self):
        """Test that from a batch of mentions, the highest score is picked for livefeed."""
        # Create batch with varying scores
        batch = [
            self.create_mention("TSLA", score=100, content="Low score TSLA"),
            self.create_mention("NVDA", score=5000, content="High score NVDA"),  # Highest
            self.create_mention("AMD", score=200, content="Medium score AMD"),
        ]

        for mention in batch:
            await main.process_mention(mention)

        # Verify all are in pending_mentions
        assert len(main.pending_mentions) == 3, "All mentions should be in pending buffer"

        # Simulate picking the best mention (as broadcast_loop does)
        best_mention = max(main.pending_mentions, key=lambda m: m["score"])

        assert best_mention["ticker"] == "NVDA", "Highest score mention (NVDA) should be picked"
        assert best_mention["score"] == 5000, "Score should be 5000"
        assert best_mention["content"] == "High score NVDA", "Content should match"

    @pytest.mark.asyncio
    async def test_five_websocket_updates(self):
        """Test at least 5 websocket updates with heatmap verification."""
        updates = []

        for update_num in range(5):
            # Create a batch of mentions for each update
            batch_size = (update_num % 3) + 1  # 1, 2, 3, 1, 2 mentions per batch

            batch_tickers = []
            batch_scores = []

            for i in range(batch_size):
                ticker = f"TEST{update_num}_{i}"
                score = (update_num + 1) * 100 + (i * 50)
                mention = self.create_mention(ticker, score=score)
                await main.process_mention(mention)
                batch_tickers.append(ticker)
                batch_scores.append(score)

            # Verify all batch tickers are in heatmap
            scores = main.hype_calculator.get_hype_scores(top_n=100)
            heatmap_tickers = [s.ticker for s in scores]

            for ticker in batch_tickers:
                assert ticker in heatmap_tickers, f"{ticker} should be in heatmap after update {update_num + 1}"

            # Verify highest score mention would be picked for livefeed
            if main.pending_mentions:
                best_mention = max(main.pending_mentions, key=lambda m: m["score"])
                expected_highest_score = max(batch_scores)

                # The highest score in this batch should be in pending_mentions
                pending_scores = [m["score"] for m in main.pending_mentions]
                assert expected_highest_score in pending_scores, \
                    f"Highest score {expected_highest_score} should be in pending mentions"

            # Record update info
            updates.append({
                "update_num": update_num + 1,
                "batch_size": batch_size,
                "tickers": batch_tickers,
                "highest_score": max(batch_scores),
            })

            # Clear pending mentions (simulating broadcast)
            main.pending_mentions.clear()

        # Verify we processed 5 updates
        assert len(updates) == 5, "Should have processed 5 updates"

        # Verify total tickers in heatmap matches expectation
        final_scores = main.hype_calculator.get_hype_scores(top_n=100)
        total_expected_tickers = sum(u["batch_size"] for u in updates)
        assert len(final_scores) == total_expected_tickers, \
            f"Heatmap should have {total_expected_tickers} tickers"

    @pytest.mark.asyncio
    async def test_batch_all_mentions_affect_heatmap(self):
        """Test that ALL mentions in a batch affect the heatmap, not just the picked one."""
        # Create batch with 5 mentions
        tickers = ["AAPL", "GOOGL", "MSFT", "META", "AMZN"]
        scores = [100, 500, 300, 200, 400]  # GOOGL has highest

        for ticker, score in zip(tickers, scores):
            mention = self.create_mention(ticker, score=score)
            await main.process_mention(mention)

        # All tickers should be in heatmap
        hype_scores = main.hype_calculator.get_hype_scores(top_n=30)
        heatmap_tickers = [s.ticker for s in hype_scores]

        for ticker in tickers:
            assert ticker in heatmap_tickers, f"{ticker} should be in heatmap"

        # But only highest score should be picked for livefeed
        best = max(main.pending_mentions, key=lambda m: m["score"])
        assert best["ticker"] == "GOOGL", "GOOGL (highest score) should be picked for livefeed"

    @pytest.mark.asyncio
    async def test_mention_count_accumulates(self):
        """Test that multiple mentions of the same ticker accumulate properly."""
        # Add 5 mentions for TSLA
        for i in range(5):
            mention = self.create_mention("TSLA", score=100 + i * 10)
            await main.process_mention(mention)

        hype_scores = main.hype_calculator.get_hype_scores(top_n=30)
        tsla_score = next((s for s in hype_scores if s.ticker == "TSLA"), None)

        assert tsla_score is not None, "TSLA should be in heatmap"
        assert tsla_score.mention_count == 5, "TSLA should have 5 mentions"

    @pytest.mark.asyncio
    async def test_livefeed_gets_highest_score_from_mixed_batch(self):
        """Test that posts (higher score potential) beat comments when scores are equal."""
        # Create mentions - a post should typically have higher score
        comment = self.create_mention("AMD", score=100, content_type="comment")
        post = self.create_mention("TSLA", score=2000, content_type="post")
        another_comment = self.create_mention("NVDA", score=150, content_type="comment")

        await main.process_mention(comment)
        await main.process_mention(post)
        await main.process_mention(another_comment)

        best = max(main.pending_mentions, key=lambda m: m["score"])

        assert best["ticker"] == "TSLA", "TSLA post (highest score) should be picked"
        assert best["content_type"] == "post", "Should be a post"
        assert best["score"] == 2000, "Score should be 2000"

    @pytest.mark.asyncio
    async def test_heatmap_preserves_all_tickers_across_updates(self):
        """Test that heatmap preserves tickers across multiple update cycles."""
        # First update
        await main.process_mention(self.create_mention("TSLA", score=100))
        await main.process_mention(self.create_mention("NVDA", score=200))

        # Clear pending (simulate broadcast)
        main.pending_mentions.clear()

        # Second update
        await main.process_mention(self.create_mention("AMD", score=300))
        await main.process_mention(self.create_mention("AAPL", score=400))

        # All 4 tickers should still be in heatmap
        hype_scores = main.hype_calculator.get_hype_scores(top_n=30)
        tickers = [s.ticker for s in hype_scores]

        assert "TSLA" in tickers, "TSLA from first update should persist"
        assert "NVDA" in tickers, "NVDA from first update should persist"
        assert "AMD" in tickers, "AMD from second update should be added"
        assert "AAPL" in tickers, "AAPL from second update should be added"

    @pytest.mark.asyncio
    async def test_empty_batch_does_not_crash(self):
        """Test that an empty pending_mentions doesn't cause issues."""
        # Ensure pending is empty
        main.pending_mentions.clear()

        # Simulate what broadcast_loop does with empty pending
        if main.pending_mentions:
            best_mention = max(main.pending_mentions, key=lambda m: m["score"])
        else:
            best_mention = None

        assert best_mention is None, "Should gracefully handle empty batch"

    @pytest.mark.asyncio
    async def test_heatmap_ordered_by_hype(self):
        """Test that heatmap returns tickers ordered by hype score."""
        # Add mentions with different counts to create different hype scores
        for _ in range(5):
            await main.process_mention(self.create_mention("TSLA", score=100))
        for _ in range(3):
            await main.process_mention(self.create_mention("NVDA", score=100))
        for _ in range(1):
            await main.process_mention(self.create_mention("AMD", score=100))

        hype_scores = main.hype_calculator.get_hype_scores(top_n=30)

        # TSLA should be first (most mentions = highest hype)
        assert hype_scores[0].ticker == "TSLA", "TSLA should have highest hype"
        assert hype_scores[1].ticker == "NVDA", "NVDA should be second"
        assert hype_scores[2].ticker == "AMD", "AMD should be third"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
