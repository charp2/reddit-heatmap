"""
FastAPI server for Reddit Stock Heatmap.
Provides WebSocket endpoint for real-time updates and REST API for stats.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import init_db, add_mention, get_recent_mentions, get_ticker_stats
from hype_calculator import HypeCalculator
from reddit_stream import has_reddit_credentials
from mock_stream import stream_mock_mentions, generate_initial_data, RedditMention

# Load environment variables
load_dotenv()

# Check if we're in demo mode
DEMO_MODE = not has_reddit_credentials()

# Global state
hype_calculator = HypeCalculator()
connected_clients: Set[WebSocket] = set()
stream_task = None


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


async def process_mention(mention: RedditMention):
    """Process a new mention: store in DB, update hype, broadcast."""
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

    # Get updated hype scores
    hype_scores = hype_calculator.get_hype_scores(top_n=30)
    stats = hype_calculator.get_stats()

    # Broadcast to clients
    await broadcast_update({
        "type": "update",
        "data": {
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
            "latest": {
                "ticker": mention.ticker,
                "content": mention.content,
                "sentiment": mention.sentiment,
                "source": mention.source,
                "author": mention.author,
                "content_type": mention.content_type,
                "timestamp": mention.created_at.isoformat(),
            },
            "stats": stats,
        },
        "demo_mode": DEMO_MODE,
        "timestamp": datetime.now().isoformat(),
    })


async def run_stream():
    """Run the Reddit/mock stream and process mentions."""
    if DEMO_MODE:
        print("🎭 Running in DEMO MODE (no Reddit credentials)")
        print("   Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to use live data")

        # Generate initial batch of data
        initial_mentions = await generate_initial_data(count=30)
        for mention in initial_mentions:
            hype_calculator.add_mention(
                ticker=mention.ticker,
                content_type=mention.content_type,
                sentiment=mention.sentiment,
                timestamp=mention.created_at,
            )

        # Stream mock data
        async for mention in stream_mock_mentions(interval_range=(1.5, 4.0)):
            await process_mention(mention)
    else:
        print("🔴 Running with LIVE Reddit data")
        # Import here to avoid loading PRAW if not needed
        from reddit_stream import stream_submissions

        async for mention in stream_submissions():
            await process_mention(mention)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global stream_task

    # Initialize database
    await init_db()

    # Start streaming task
    stream_task = asyncio.create_task(run_stream())

    yield

    # Cleanup
    if stream_task:
        stream_task.cancel()
        try:
            await stream_task
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

    # Send initial state
    hype_scores = hype_calculator.get_hype_scores(top_n=30)
    stats = hype_calculator.get_stats()

    await websocket.send_text(json.dumps({
        "type": "init",
        "data": {
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
        },
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

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=["."],
    )
