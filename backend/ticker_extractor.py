"""
Ticker extraction with entity resolution.
Extracts stock tickers from text using:
1. Cashtags ($TSLA)
2. Standalone uppercase tickers (TSLA)
3. Entity resolution (Tesla, Elon -> TSLA)
"""

import re
import json
from pathlib import Path
from typing import Set

# Load ticker whitelist and excluded words
DATA_DIR = Path(__file__).parent
with open(DATA_DIR / "tickers.json") as f:
    ticker_data = json.load(f)
    VALID_TICKERS: Set[str] = set(ticker_data["tickers"])
    EXCLUDED_WORDS: Set[str] = set(ticker_data["excluded_words"])

# Load entity mappings
with open(DATA_DIR / "entity_mappings.json") as f:
    ENTITY_MAPPINGS = json.load(f)

# Build reverse lookup: entity -> ticker
ENTITY_TO_TICKER: dict[str, str] = {}
for ticker, mappings in ENTITY_MAPPINGS.items():
    for name in mappings.get("names", []):
        ENTITY_TO_TICKER[name.lower()] = ticker
    for person in mappings.get("people", []):
        ENTITY_TO_TICKER[person.lower()] = ticker
    for product in mappings.get("products", []):
        ENTITY_TO_TICKER[product.lower()] = ticker

# Compile patterns
CASHTAG_PATTERN = re.compile(r'\$([A-Z]{1,5})\b')
STANDALONE_PATTERN = re.compile(r'\b([A-Z]{2,5})\b')


def extract_tickers(text: str) -> Set[str]:
    """
    Extract stock tickers from text.

    Args:
        text: Raw text from Reddit post/comment

    Returns:
        Set of valid ticker symbols found
    """
    found_tickers: Set[str] = set()

    # 1. Extract cashtags ($TSLA, $GME)
    for match in CASHTAG_PATTERN.finditer(text):
        ticker = match.group(1)
        if ticker in VALID_TICKERS:
            found_tickers.add(ticker)

    # 2. Extract standalone uppercase tickers
    for match in STANDALONE_PATTERN.finditer(text):
        ticker = match.group(1)
        if ticker in VALID_TICKERS and ticker not in EXCLUDED_WORDS:
            found_tickers.add(ticker)

    # 3. Entity resolution (case-insensitive)
    text_lower = text.lower()
    for entity, ticker in ENTITY_TO_TICKER.items():
        # Use word boundaries to avoid partial matches
        pattern = rf'\b{re.escape(entity)}\b'
        if re.search(pattern, text_lower):
            found_tickers.add(ticker)

    return found_tickers


def extract_tickers_with_context(text: str) -> list[dict]:
    """
    Extract tickers with additional context about how they were matched.

    Args:
        text: Raw text from Reddit post/comment

    Returns:
        List of dicts with ticker and match_type
    """
    results = []
    seen_tickers: Set[str] = set()

    # 1. Cashtags (highest priority)
    for match in CASHTAG_PATTERN.finditer(text):
        ticker = match.group(1)
        if ticker in VALID_TICKERS and ticker not in seen_tickers:
            results.append({"ticker": ticker, "match_type": "cashtag"})
            seen_tickers.add(ticker)

    # 2. Standalone tickers
    for match in STANDALONE_PATTERN.finditer(text):
        ticker = match.group(1)
        if ticker in VALID_TICKERS and ticker not in EXCLUDED_WORDS and ticker not in seen_tickers:
            results.append({"ticker": ticker, "match_type": "standalone"})
            seen_tickers.add(ticker)

    # 3. Entity resolution
    text_lower = text.lower()
    for entity, ticker in ENTITY_TO_TICKER.items():
        if ticker not in seen_tickers:
            pattern = rf'\b{re.escape(entity)}\b'
            if re.search(pattern, text_lower):
                results.append({"ticker": ticker, "match_type": "entity", "matched_entity": entity})
                seen_tickers.add(ticker)

    return results


if __name__ == "__main__":
    # Test cases
    test_texts = [
        "Just bought $TSLA calls, Elon is going to make us rich!",
        "Tesla is undervalued, cybertruck deliveries starting soon",
        "GME and AMC to the moon! Ryan Cohen tweeted again",
        "Should I buy NVDA? Jensen at GTC was amazing with the H100",
        "Apple releasing new iPhone, Tim Cook said vision pro is selling well",
        "I AM going to BUY some stocks TODAY",  # Should not match I, AM, BUY, etc.
    ]

    for text in test_texts:
        tickers = extract_tickers(text)
        print(f"\nText: {text[:60]}...")
        print(f"Tickers: {tickers}")

        detailed = extract_tickers_with_context(text)
        for item in detailed:
            print(f"  - {item}")
