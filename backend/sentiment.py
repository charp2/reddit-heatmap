"""
Sentiment analysis using VADER.
VADER (Valence Aware Dictionary and sEntiment Reasoner) is well-suited
for social media text with its handling of emoticons, slang, and emphasis.
"""

import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Download VADER lexicon if not present
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)

# Initialize analyzer
_analyzer = SentimentIntensityAnalyzer()

# Add custom financial/WSB terms to lexicon
CUSTOM_LEXICON = {
    # Bullish terms
    "moon": 3.0,
    "mooning": 3.5,
    "rocket": 2.5,
    "tendies": 2.0,
    "diamond hands": 2.5,
    "diamondhands": 2.5,
    "hodl": 2.0,
    "bullish": 3.0,
    "calls": 1.5,
    "yolo": 1.5,
    "squeeze": 2.0,
    "lambo": 2.5,
    "ape": 1.5,
    "apes": 1.5,
    "hold": 1.0,
    "holding": 1.0,
    "buy": 1.5,
    "buying": 1.5,
    "long": 1.0,
    "undervalued": 2.0,
    "breakout": 2.0,
    "rip": 2.0,
    "ripping": 2.5,
    "pump": 1.5,
    "gamma": 1.0,
    "short squeeze": 3.0,

    # Bearish terms
    "dump": -2.0,
    "dumping": -2.5,
    "paper hands": -2.0,
    "paperhands": -2.0,
    "bearish": -3.0,
    "puts": -1.5,
    "short": -1.0,
    "shorting": -1.5,
    "sell": -1.5,
    "selling": -1.5,
    "bag holder": -2.5,
    "bagholder": -2.5,
    "bagholding": -2.5,
    "overvalued": -2.0,
    "crash": -3.0,
    "crashing": -3.0,
    "tank": -2.5,
    "tanking": -3.0,
    "drill": -2.0,
    "drilling": -2.5,
    "red": -1.0,
    "loss": -2.0,
    "losses": -2.0,
    "down": -1.0,
    "dip": -0.5,  # Could be "buy the dip" so mild negative

    # Neutral/context-dependent
    "retard": 0.0,  # WSB term of endearment
    "retarded": 0.0,
    "autist": 0.0,
    "smooth brain": 0.0,
    "wife's boyfriend": 0.0,
    "wendys": 0.0,
}

# Update VADER lexicon with custom terms
for term, score in CUSTOM_LEXICON.items():
    _analyzer.lexicon[term] = score


def analyze_sentiment(text: str) -> dict:
    """
    Analyze sentiment of text using VADER.

    Args:
        text: Raw text from Reddit post/comment

    Returns:
        Dict with sentiment scores:
        - compound: Overall sentiment (-1 to 1)
        - positive: Positive sentiment proportion
        - negative: Negative sentiment proportion
        - neutral: Neutral sentiment proportion
    """
    scores = _analyzer.polarity_scores(text)
    return {
        "compound": scores["compound"],
        "positive": scores["pos"],
        "negative": scores["neg"],
        "neutral": scores["neu"],
    }


def get_sentiment_label(compound_score: float) -> str:
    """
    Convert compound score to human-readable label.

    Args:
        compound_score: VADER compound score (-1 to 1)

    Returns:
        Label: 'bullish', 'bearish', or 'neutral'
    """
    if compound_score >= 0.05:
        return "bullish"
    elif compound_score <= -0.05:
        return "bearish"
    else:
        return "neutral"


if __name__ == "__main__":
    # Test cases
    test_texts = [
        "TSLA to the moon! 🚀🚀🚀 Diamond hands baby!",
        "Just bought calls, feeling bullish on this one",
        "This stock is tanking, I'm a bag holder now 😭",
        "Sold my puts, this thing is dumping hard",
        "Not sure if I should buy or sell here",
        "GME earnings report released today",
    ]

    for text in test_texts:
        result = analyze_sentiment(text)
        label = get_sentiment_label(result["compound"])
        print(f"\nText: {text[:50]}...")
        print(f"Sentiment: {label} (compound: {result['compound']:.3f})")
