"""
FastAPI server for Reddit Stock Heatmap.
Provides WebSocket endpoint for real-time updates and REST API for stats.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Set, Dict, List
from collections import deque

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import init_db, add_mention, get_recent_mentions, get_ticker_stats
from hype_calculator import HypeCalculator
from models import RedditMention
from reddit_stream import has_reddit_credentials
from mock_stream import stream_mock_mentions

# Load environment variables
load_dotenv()

# Check if we're in demo mode
DEMO_MODE = not has_reddit_credentials()

# Global state
hype_calculator = HypeCalculator()
connected_clients: Set[WebSocket] = set()

# Pending mentions buffer for batching
pending_mentions: List[dict] = []
BROADCAST_INTERVAL = 3.0  # seconds between broadcasts


async def broadcast_update(data: dict):
    """Broadcast update to all connected WebSocket clients."""
    if not connected_clients:
        return

    message = json.dumps(data)
    disconnected = set()

    for client in connected_clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.add(client)

    # Clean up disconnected clients
    for client in disconnected:
        connected_clients.discard(client)


def calculate_influence_score(mention_data: dict, top_tickers: set) -> float:
    """
    Calculate influence score for a mention.
    Higher score = more influential = should be featured.

    Factors:
    - Post vs comment (posts are 1.5x more influential)
    - Sentiment strength (stronger sentiment = more influential)
    - Top ticker bonus (mentions of trending tickers are more influential)
    """
    # Base weight for post vs comment
    type_weight = 1.5 if mention_data["content_type"] == "post" else 1.0

    # Sentiment strength (0 to 1 scale)
    sentiment_strength = abs(mention_data["sentiment"])

    # Bonus if this is a top-5 ticker
    ticker_bonus = 2.0 if mention_data["ticker"] in top_tickers else 1.0

    return type_weight * (1 + sentiment_strength) * ticker_bonus


def get_most_influential_mention(mentions: List[dict], top_tickers: set) -> dict | None:
    """Pick the most influential mention from a list."""
    if not mentions:
        return None

    best_mention = None
    best_score = -1

    for mention in mentions:
        score = calculate_influence_score(mention, top_tickers)
        if score > best_score:
            best_score = score
            best_mention = mention

    return best_mention


async def process_mention(mention: RedditMention):
    """Process a new mention: update hype calculator and buffer for broadcast."""
    global pending_mentions

    # Add to hype calculator
    hype_calculator.add_mention(
        ticker=mention.ticker,
        content_type=mention.content_type,
        sentiment=mention.sentiment,
        timestamp=mention.created_at,
    )

    # Store in database
    await add_mention(
        ticker=mention.ticker,
        source=mention.source,
        content_type=mention.content_type,
        content=mention.content,
        sentiment=mention.sentiment,
        author=mention.author,
        permalink=mention.permalink,
    )

    # Buffer the mention for batch processing
    mention_data = {
        "ticker": mention.ticker,
        "content": mention.content,
        "sentiment": mention.sentiment,
        "source": mention.source,
        "author": mention.author,
        "content_type": mention.content_type,
        "timestamp": mention.created_at.isoformat(),
        "score": mention.score,
    }
    pending_mentions.append(mention_data)


async def broadcast_loop():
    """Periodically broadcast updates with the most influential mention."""
    global pending_mentions

    while True:
        await asyncio.sleep(BROADCAST_INTERVAL)

        if not connected_clients:
            # No clients, just clear the buffer
            pending_mentions = []
            continue

        # Get current hype scores
        hype_scores = hype_calculator.get_hype_scores(top_n=30)
        stats = hype_calculator.get_stats()

        # Get top 5 tickers for influence calculation
        top_tickers = set(s.ticker for s in hype_scores[:5])

        # Build update payload
        update_data = {
            "heatmap": [
                {
                    "ticker": s.ticker,
                    "hype": s.hype,
                    "sentiment": s.avg_sentiment,
                    "mentions": s.mention_count,
                    "velocity": s.velocity,
                }
                for s in hype_scores
            ],
            "stats": stats,
        }

        # Pick the highest-score mention from the batch for the live feed
        # This ensures the most popular content is shown without overwhelming the user
        if pending_mentions:
            # Sort by score descending and pick the top one
            best_mention = max(pending_mentions, key=lambda m: m["score"])
            update_data["latest"] = best_mention
            # Clear the buffer
            pending_mentions = []

        # Broadcast to all clients
        await broadcast_update({
            "type": "update",
            "data": update_data,
            "demo_mode": DEMO_MODE,
            "timestamp": datetime.now().isoformat(),
        })


async def run_stream():
    """Run the Reddit/mock stream and process mentions."""
    try:
        if DEMO_MODE:
            print("🎭 Running in DEMO MODE (no Reddit credentials)", flush=True)
            print("   Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to use live data", flush=True)
            print("   Starting with empty state - data will populate as mentions arrive", flush=True)

            # Stream mock data (slower interval for smoother updates)
            # No initial data - starts empty as requested
            async for mention in stream_mock_mentions(interval_range=(2.5, 5.0)):
                await process_mention(mention)
        else:
            print("🔴 Running with LIVE Reddit data")
            # Import here to avoid loading PRAW if not needed
            from reddit_stream import stream_submissions

            async for mention in stream_submissions():
                await process_mention(mention)
    except Exception as e:
        print(f"❌ Stream error: {e}")
        import traceback
        traceback.print_exc()


def reset_state():
    """Reset all in-memory state for a clean start."""
    global hype_calculator, pending_mentions
    hype_calculator = HypeCalculator()
    pending_mentions = []
    print("✅ State reset - starting fresh", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    stream_task = None
    broadcast_task = None

    # Reset state for clean start
    reset_state()

    # Initialize database
    await init_db()

    # Start streaming task (generates mentions)
    stream_task = asyncio.create_task(run_stream())

    # Start broadcast loop (sends updates to clients at fixed interval)
    broadcast_task = asyncio.create_task(broadcast_loop())

    yield

    # Cleanup
    for task in [stream_task, broadcast_task]:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


# Create FastAPI app
app = FastAPI(
    title="Reddit Stock Heatmap",
    description="Real-time stock mention tracking from Reddit",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "demo_mode": DEMO_MODE,
        "message": "Reddit Stock Heatmap API",
    }


@app.get("/api/stats")
async def get_stats():
    """Get current statistics."""
    return {
        "hype_scores": [
            {
                "ticker": s.ticker,
                "hype": s.hype,
                "sentiment": s.avg_sentiment,
                "mentions": s.mention_count,
                "velocity": s.velocity,
            }
            for s in hype_calculator.get_hype_scores(top_n=30)
        ],
        "stats": hype_calculator.get_stats(),
        "demo_mode": DEMO_MODE,
    }


@app.get("/api/mentions")
async def get_mentions(limit: int = 50):
    """Get recent mentions from database."""
    mentions = await get_recent_mentions(limit=limit)
    return {
        "mentions": mentions,
        "demo_mode": DEMO_MODE,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    connected_clients.add(websocket)

    # Send current state to new client
    hype_scores = hype_calculator.get_hype_scores(top_n=30)
    stats = hype_calculator.get_stats()

    # Build init data - always send empty arrays, never undefined
    init_data = {
        "heatmap": [
            {
                "ticker": s.ticker,
                "hype": s.hype,
                "sentiment": s.avg_sentiment,
                "mentions": s.mention_count,
                "velocity": s.velocity,
            }
            for s in hype_scores
        ],
        "stats": stats,
        # No "latest" on init - feed starts empty
    }

    await websocket.send_text(json.dumps({
        "type": "init",
        "data": init_data,
        "demo_mode": DEMO_MODE,
        "timestamp": datetime.now().isoformat(),
    }))

    try:
        while True:
            # Keep connection alive, handle any client messages
            data = await websocket.receive_text()
            # Could handle client commands here if needed
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
    except Exception:
        connected_clients.discard(websocket)


if __name__ == "__main__":
    import uvicorn
    import sys

    # Force unbuffered output
    sys.stdout.reconfigure(line_buffering=True)

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=["."],
    )
