"""
data_generator.py
Generates anonymized synthetic text data simulating mental health survey responses
across different regions and time periods.
"""
import random
import numpy as np

REGIONS = [
    "Northeast", "Southeast", "Midwest", "Southwest", "West Coast", "Pacific Northwest"
]

# Anonymized text templates — no real identifiers
POSITIVE_TEMPLATES = [
    "Feeling much more connected to my community lately and finding support when needed.",
    "The local counseling services have been incredibly helpful for managing daily stress.",
    "Noticed significant improvement in work-life balance after joining a peer support group.",
    "Mental health resources in this area have made a real difference in my well-being.",
    "Feeling hopeful and supported by friends and family through recent challenges.",
    "Access to telehealth therapy has been a game-changer for managing anxiety.",
    "Community wellness programs have provided excellent coping strategies.",
    "Regular mindfulness sessions at the community center have reduced my stress levels.",
    "The support network here is strong; people look out for each other.",
    "Grateful for the mental health awareness initiatives that helped me seek help early.",
]

NEUTRAL_TEMPLATES = [
    "Mental health awareness has improved but access to care remains inconsistent.",
    "Some days are harder than others; trying to maintain a balanced routine.",
    "The wait times for counseling services are long but the quality is acceptable.",
    "Workplace stress is manageable with occasional support from HR programs.",
    "Community support exists but awareness about mental health services could be better.",
    "Navigating mental health resources is complicated but getting easier over time.",
    "Local programs are available but participation rates seem low.",
    "Stress levels fluctuate with seasonal changes and work demands.",
    "Insurance coverage for mental health treatment is improving but gaps remain.",
    "Peer support groups are helpful though not always available when needed.",
]

NEGATIVE_TEMPLATES = [
    "Feeling overwhelmed by work pressures and struggling to find adequate support.",
    "Mental health services in this region are severely underfunded and hard to access.",
    "Long waiting lists for therapy have left many people without timely support.",
    "Social isolation has worsened significantly affecting daily functioning.",
    "The stigma around seeking mental health help remains a major barrier in this community.",
    "Cost of mental health care is prohibitive for many residents in this area.",
    "Experiencing persistent anxiety and depression with limited access to professionals.",
    "Community mental health centers are overcrowded and understaffed.",
    "Recent job losses have significantly impacted the mental well-being of residents.",
    "Lack of culturally competent mental health services is a growing concern.",
]

# Regional bias factors: positive tendency (0=very negative, 1=very positive)
REGION_BIAS = {
    "Northeast": 0.55,
    "Southeast": 0.45,
    "Midwest": 0.50,
    "Southwest": 0.48,
    "West Coast": 0.60,
    "Pacific Northwest": 0.57,
}

# Monthly trend factors (simulate seasonal variation)
MONTH_FACTORS = {
    1: -0.05,  # Jan - post-holiday slump
    2: -0.03,
    3: 0.02,   # Spring improvement
    4: 0.05,
    5: 0.07,
    6: 0.06,
    7: 0.04,
    8: 0.03,
    9: 0.01,
    10: -0.02, # Autumn dip
    11: -0.04,
    12: -0.06, # Holiday stress
}


def generate_text_samples(region: str, month: int, year: int = 2024, count: int = 30) -> list[dict]:
    """Generate anonymized text samples for a given region and month."""
    random.seed(hash(f"{region}-{month}-{year}"))
    np.random.seed(hash(f"{region}-{month}-{year}") % (2**31))

    bias = REGION_BIAS.get(region, 0.5)
    month_adj = MONTH_FACTORS.get(month, 0.0)
    effective_bias = min(0.9, max(0.1, bias + month_adj))

    samples = []
    for i in range(count):
        r = random.random()
        if r < effective_bias * 0.6:
            text = random.choice(POSITIVE_TEMPLATES)
            sentiment_hint = "positive"
        elif r < effective_bias * 0.6 + 0.35:
            text = random.choice(NEUTRAL_TEMPLATES)
            sentiment_hint = "neutral"
        else:
            text = random.choice(NEGATIVE_TEMPLATES)
            sentiment_hint = "negative"

        samples.append({
            "id": f"ANON-{region[:3].upper()}-{year}{month:02d}-{i:04d}",
            "text": text,
            "region": region,
            "month": month,
            "year": year,
            "sentiment_hint": sentiment_hint
        })

    return samples


def generate_all_samples(months: list[int] = None, year: int = 2024) -> list[dict]:
    """Generate samples for all regions across given months."""
    if months is None:
        months = list(range(1, 13))

    all_samples = []
    for region in REGIONS:
        for month in months:
            all_samples.extend(generate_text_samples(region, month, year))

    return all_samples


if __name__ == "__main__":
    samples = generate_text_samples("Northeast", 6)
    print(f"Generated {len(samples)} samples")
    for s in samples[:3]:
        print(f"  [{s['id']}] ({s['sentiment_hint']}) {s['text'][:60]}...")
