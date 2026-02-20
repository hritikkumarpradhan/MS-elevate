"""
chart_generator.py
Generates Matplotlib line charts for mental health sentiment trends.
Uses a professional blue-teal color palette matching the dashboard UI.
"""
import io
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Dashboard color palette
PALETTE = {
    "background":   "#0D1B2A",
    "card_bg":      "#1A2C42",
    "grid":         "#1E3A5F",
    "teal_accent":  "#00BFA5",
    "blue_primary": "#1B8ECA",
    "teal_light":   "#4DD0C4",
    "amber":        "#FFB347",
    "text_primary": "#E8F4F8",
    "text_muted":   "#7BA7C2",
    "positive":     "#00BFA5",
    "negative":     "#E57373",
    "neutral":      "#90A4AE",
}

REGION_COLORS = [
    "#00BFA5",  # teal
    "#1B8ECA",  # blue
    "#4DD0C4",  # light teal
    "#64B5F6",  # light blue
    "#80CBC4",  # muted teal
    "#42A5F5",  # bright blue
]


def _apply_dark_theme(fig, ax):
    """Apply the dashboard dark theme to a Matplotlib figure."""
    fig.patch.set_facecolor(PALETTE["card_bg"])
    ax.set_facecolor(PALETTE["background"])
    ax.tick_params(colors=PALETTE["text_muted"], labelsize=9)
    ax.xaxis.label.set_color(PALETTE["text_primary"])
    ax.yaxis.label.set_color(PALETTE["text_primary"])
    ax.title.set_color(PALETTE["text_primary"])
    for spine in ax.spines.values():
        spine.set_edgecolor(PALETTE["grid"])
    ax.grid(True, color=PALETTE["grid"], linewidth=0.6, linestyle="--", alpha=0.7)
    ax.set_axisbelow(True)


def generate_trend_chart(
    region_data: dict[str, list],
    title: str = "Sentiment Trend Over Time",
    width: int = 900,
    height: int = 420,
    dpi: int = 100
) -> bytes:
    """
    Generate a multi-region sentiment trend chart.

    Args:
        region_data: dict mapping region name -> list of (month_label, avg_sentiment)
        title: chart title
        width, height: pixel dimensions
        dpi: dots per inch

    Returns:
        PNG bytes
    """
    fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    _apply_dark_theme(fig, ax)

    legend_patches = []
    for i, (region, data_points) in enumerate(region_data.items()):
        if not data_points:
            continue

        color = REGION_COLORS[i % len(REGION_COLORS)]
        labels = [p["month_label"] for p in data_points]
        scores = [p["avg_sentiment"] for p in data_points]
        x = np.arange(len(labels))

        # Main trend line
        ax.plot(
            x, scores, color=color, linewidth=2.5,
            marker="o", markersize=5, markerfacecolor=color,
            markeredgecolor=PALETTE["card_bg"], markeredgewidth=1.5,
            zorder=3, label=region
        )

        # Shaded confidence band (±std if available)
        if "std_dev" in data_points[0]:
            stds = [p.get("std_dev", 5) for p in data_points]
            upper = [min(100, s + sd) for s, sd in zip(scores, stds)]
            lower = [max(0, s - sd) for s, sd in zip(scores, stds)]
            ax.fill_between(x, lower, upper, color=color, alpha=0.12, zorder=2)

        legend_patches.append(
            mpatches.Patch(color=color, label=region)
        )

        # Set x tick labels from the first (or only) region
        if i == 0:
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8.5)

    # Reference lines
    ax.axhline(y=50, color=PALETTE["text_muted"], linewidth=1, linestyle="--",
               alpha=0.5, label="Neutral (50)")
    ax.axhline(y=65, color=PALETTE["positive"], linewidth=0.8, linestyle=":",
               alpha=0.4, label="Positive threshold")
    ax.axhline(y=35, color=PALETTE["negative"], linewidth=0.8, linestyle=":",
               alpha=0.4, label="Concern threshold")

    # Labels and formatting
    ax.set_xlabel("Month", fontsize=11, labelpad=8)
    ax.set_ylabel("Sentiment Score (0–100)", fontsize=11, labelpad=8)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=16,
                 color=PALETTE["text_primary"])
    ax.set_ylim(0, 100)
    ax.set_xlim(-0.3, len(list(region_data.values())[0]) - 0.7 if region_data else 11)

    # Legend
    legend = ax.legend(
        handles=legend_patches,
        loc="upper right",
        facecolor=PALETTE["card_bg"],
        edgecolor=PALETTE["grid"],
        labelcolor=PALETTE["text_primary"],
        fontsize=9,
        framealpha=0.9,
    )

    # Watermark
    fig.text(0.99, 0.01, "Mental Health Trend Monitor | NLP Pipeline v1.0",
             ha="right", va="bottom", fontsize=7, color=PALETTE["text_muted"], alpha=0.6)

    plt.tight_layout(pad=1.5)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=fig.get_facecolor(), dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_comparison_bar_chart(regions_summary: list[dict], width: int = 800, height: int = 380, dpi: int = 100) -> bytes:
    """Generate a horizontal bar chart comparing overall sentiment across regions."""
    fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    _apply_dark_theme(fig, ax)

    regions = [d["region"] for d in regions_summary]
    scores = [d["overall_avg"] for d in regions_summary]
    colors = [PALETTE["positive"] if s >= 50 else PALETTE["negative"] for s in scores]

    y = np.arange(len(regions))
    bars = ax.barh(y, scores, color=colors, height=0.55, zorder=3,
                   edgecolor=PALETTE["card_bg"], linewidth=0.5)

    # Add value labels
    for bar, score in zip(bars, scores):
        ax.text(score + 1, bar.get_y() + bar.get_height() / 2,
                f"{score:.1f}", va="center", ha="left",
                color=PALETTE["text_primary"], fontsize=9, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(regions, fontsize=10)
    ax.set_xlabel("Average Sentiment Score (0–100)", fontsize=10.5, labelpad=8)
    ax.set_title("Regional Sentiment Comparison — 2024", fontsize=13,
                 fontweight="bold", pad=14, color=PALETTE["text_primary"])
    ax.set_xlim(0, 110)
    ax.axvline(x=50, color=PALETTE["text_muted"], linewidth=1, linestyle="--", alpha=0.5)

    plt.tight_layout(pad=1.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=fig.get_facecolor(), dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


if __name__ == "__main__":
    # Quick test
    test_data = {
        "Northeast": [
            {"month_label": f"Month {i}", "avg_sentiment": 50 + i * 1.5, "std_dev": 5}
            for i in range(12)
        ]
    }
    png = generate_trend_chart(test_data, "Test Chart")
    with open("test_chart.png", "wb") as f:
        f.write(png)
    print(f"Chart generated: {len(png):,} bytes")
