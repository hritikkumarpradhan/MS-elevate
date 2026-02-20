"""
data_pipeline.py
Simulates a real NLP pipeline using:
  - spaCy: tokenization, NER, linguistic features
  - NLTK VADER: sentiment intensity analysis
Processes anonymized text samples and returns structured sentiment data.
"""
import re
import statistics
from datetime import datetime

import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Download required NLTK data if not present
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon", quiet=True)

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)

# Try to load spaCy model
try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
    except OSError:
        print("[Pipeline] spaCy model 'en_core_web_sm' not found. Using fallback tokenizer.")
        SPACY_AVAILABLE = False
except ImportError:
    print("[Pipeline] spaCy not installed. Using fallback tokenizer.")
    SPACY_AVAILABLE = False

# Initialize VADER sentiment analyzer
vader = SentimentIntensityAnalyzer()

MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
}


def preprocess_text(text: str) -> str:
    """Clean and normalize text for NLP processing."""
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[^\w\s.,!?\'"-]', '', text)
    return text


def extract_spacy_features(text: str) -> dict:
    """Use spaCy to extract linguistic features from text."""
    if not SPACY_AVAILABLE:
        # Fallback: basic word count analysis
        words = text.split()
        return {
            "token_count": len(words),
            "entities": [],
            "key_phrases": words[:5],
            "has_negation": any(w in words for w in ["not", "no", "never", "without"]),
        }

    doc = nlp(text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    # Filter to relevant entity types for mental health context
    relevant_labels = {"ORG", "GPE", "PERSON", "FACILITY", "NORP"}
    relevant_entities = [(t, l) for t, l in entities if l in relevant_labels]

    # Extract noun chunks as key phrases
    key_phrases = [chunk.text for chunk in doc.noun_chunks][:5]

    # Check for negation patterns
    has_negation = any(
        token.dep_ == "neg" or token.text.lower() in {"not", "no", "never", "without"}
        for token in doc
    )

    return {
        "token_count": len(doc),
        "entities": relevant_entities,
        "key_phrases": key_phrases,
        "has_negation": has_negation,
    }


def compute_sentiment(text: str) -> dict:
    """
    Compute sentiment using NLTK VADER.
    Returns compound score (-1 to +1) and component scores.
    Adjusts for negation context from spaCy analysis.
    """
    cleaned = preprocess_text(text)
    spacy_features = extract_spacy_features(cleaned)
    vader_scores = vader.polarity_scores(cleaned)

    compound = vader_scores["compound"]

    # Apply a mild adjustment if spaCy detected negation not caught by VADER
    if spacy_features["has_negation"] and compound > 0.1:
        compound = max(-1.0, compound - 0.1)

    # Normalize to 0-100 scale for friendly display
    normalized_score = (compound + 1) / 2 * 100  # 0=very negative, 100=very positive

    return {
        "raw_compound": compound,
        "normalized_score": round(normalized_score, 2),
        "positive": round(vader_scores["pos"] * 100, 2),
        "negative": round(vader_scores["neg"] * 100, 2),
        "neutral": round(vader_scores["neu"] * 100, 2),
        "token_count": spacy_features["token_count"],
        "entities_found": len(spacy_features["entities"]),
    }


def process_samples(samples: list[dict]) -> list[dict]:
    """Process a list of text samples through the NLP pipeline."""
    processed = []
    for sample in samples:
        sentiment = compute_sentiment(sample["text"])
        processed.append({
            **sample,
            **sentiment,
            "processed_at": datetime.now().isoformat(),
        })
    return processed


def aggregate_by_month(processed_samples: list[dict]) -> list[dict]:
    """Aggregate processed samples into monthly sentiment averages."""
    monthly = {}
    for s in processed_samples:
        key = (s["year"], s["month"])
        if key not in monthly:
            monthly[key] = {"scores": [], "region": s["region"], "year": s["year"], "month": s["month"]}
        monthly[key]["scores"].append(s["normalized_score"])

    result = []
    for (year, month), data in sorted(monthly.items()):
        scores = data["scores"]
        result.append({
            "region": data["region"],
            "year": year,
            "month": month,
            "month_label": f"{MONTH_NAMES[month]} {year}",
            "avg_sentiment": round(statistics.mean(scores), 2),
            "std_dev": round(statistics.stdev(scores) if len(scores) > 1 else 0, 2),
            "sample_count": len(scores),
            "min_score": round(min(scores), 2),
            "max_score": round(max(scores), 2),
        })

    return result


def run_pipeline(region: str, months: list[int] = None, year: int = 2024) -> dict:
    """
    Run the full NLP pipeline for a region.
    Returns time-series sentiment data and pipeline metadata.
    """
    from data_generator import generate_text_samples

    if months is None:
        months = list(range(1, 13))

    all_processed = []
    for month in months:
        samples = generate_text_samples(region, month, year, count=30)
        processed = process_samples(samples)
        all_processed.extend(processed)

    monthly_agg = aggregate_by_month(all_processed)
    overall_scores = [m["avg_sentiment"] for m in monthly_agg]

    return {
        "region": region,
        "year": year,
        "monthly_data": monthly_agg,
        "overall_avg": round(statistics.mean(overall_scores), 2) if overall_scores else 0,
        "trend_direction": "improving" if overall_scores[-1] > overall_scores[0] else "declining",
        "total_samples_processed": len(all_processed),
        "spacy_available": SPACY_AVAILABLE,
        "pipeline_version": "1.0.0",
    }


if __name__ == "__main__":
    print("Running pipeline test for Northeast region...")
    result = run_pipeline("Northeast")
    print(f"Overall avg sentiment: {result['overall_avg']}")
    print(f"Trend: {result['trend_direction']}")
    print(f"Samples processed: {result['total_samples_processed']}")
    print(f"spaCy: {'available' if result['spacy_available'] else 'using fallback'}")
    for m in result["monthly_data"][:3]:
        print(f"  {m['month_label']}: {m['avg_sentiment']:.1f}/100 (n={m['sample_count']})")
