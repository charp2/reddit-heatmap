# Reddit Stock Heatmap

Real-time stock hype tracking from Reddit. Monitors r/wallstreetbets, r/stocks, and r/options for stock mentions and displays them in an interactive heatmap.

![Demo](https://via.placeholder.com/800x400?text=Reddit+Stock+Heatmap+Dashboard)

## Features

- **Real-time Heatmap**: Visual treemap showing stock "hype" - larger tiles = more mentions
- **Sentiment Analysis**: Color-coded sentiment (green = bullish, red = bearish)
- **Entity Resolution**: Recognizes "Tesla", "Elon", "Cybertruck" → TSLA
- **Live Feed**: Scrolling feed of mentions as they happen
- **Demo Mode**: Works out of the box without Reddit API credentials

## Quick Start

### 1. Start the Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download NLTK data (first run only)
python -c "import nltk; nltk.download('vader_lexicon')"

# Start the server
python main.py
```

Backend runs at `http://localhost:8000`

### 2. Start the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at `http://localhost:3000`

## Using Live Reddit Data

By default, the app runs in **Demo Mode** with simulated data.

To use live Reddit data:

1. Go to https://www.reddit.com/prefs/apps
2. Click "create another app..."
3. Select "script" type
4. Note your `client_id` (under the app name) and `client_secret`

5. Create `backend/.env`:
```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=RedditHeatmap/1.0
```

6. Restart the backend server

## Project Structure

```
reddit-heatmap/
├── backend/
│   ├── main.py              # FastAPI server + WebSocket
│   ├── reddit_stream.py     # Live Reddit streaming
│   ├── mock_stream.py       # Demo data generator
│   ├── ticker_extractor.py  # Ticker + entity extraction
│   ├── sentiment.py         # VADER sentiment analysis
│   ├── database.py          # SQLite storage
│   ├── hype_calculator.py   # Hype scoring with decay
│   ├── tickers.json         # Valid ticker whitelist
│   └── entity_mappings.json # Company/CEO → ticker mappings
├── frontend/
│   ├── app/
│   │   └── page.tsx         # Main dashboard
│   ├── components/
│   │   ├── Heatmap.tsx      # Treemap visualization
│   │   ├── LiveFeed.tsx     # Mention feed
│   │   └── StatsPanel.tsx   # Statistics display
│   └── hooks/
│       └── useWebSocket.ts  # Real-time connection
└── README.md
```

## API Endpoints

- `GET /` - Health check
- `GET /api/stats` - Current hype scores and statistics
- `GET /api/mentions?limit=50` - Recent mentions from database
- `WS /ws` - WebSocket for real-time updates

## How It Works

### Ticker Extraction
1. **Cashtags**: Matches `$TSLA`, `$GME`, etc.
2. **Standalone**: Matches uppercase `NVDA`, `AMD` against whitelist
3. **Entity Resolution**: Maps company names ("Tesla"), people ("Elon Musk"), and products ("Cybertruck") to tickers

### Hype Scoring
Uses exponential decay with 10-minute half-life:
```
hype = Σ (weight × e^(-λt))
```
- Posts weighted 1.5x vs comments
- Recent mentions matter more
- Scores update in real-time

### Sentiment Analysis
VADER with custom financial lexicon:
- "moon", "rocket", "diamond hands" → bullish
- "dump", "tank", "bag holder" → bearish

## Tech Stack

**Backend**
- Python 3.10+
- FastAPI + WebSocket
- PRAW (Reddit API)
- NLTK VADER
- SQLite

**Frontend**
- Next.js 14
- Tailwind CSS
- @visx/treemap (D3-based)
- TypeScript

## Configuration

### Environment Variables

**Backend** (`backend/.env`):
```env
REDDIT_CLIENT_ID=         # Reddit API client ID
REDDIT_CLIENT_SECRET=     # Reddit API secret
REDDIT_USER_AGENT=        # Optional, defaults to "RedditHeatmap/1.0"
PORT=8000                 # Optional, defaults to 8000
```

**Frontend** (`.env.local`):
```env
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## License

MIT
