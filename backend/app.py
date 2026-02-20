"""
app.py
Flask REST API for the Mental Health Trend Monitor dashboard.
Serves both the API endpoints and the static frontend.
"""
import sys
import os

# Add backend directory to path so we can import sibling modules
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import io
import json
import statistics

from data_generator import REGIONS
from data_pipeline import run_pipeline
from chart_generator import generate_trend_chart, generate_comparison_bar_chart

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend"),
    static_url_path="",
)
CORS(app)

# In-memory cache for pipeline results (avoid reprocessing on every request)
_pipeline_cache = {}


def get_pipeline_data(region: str, year: int = 2024) -> dict:
    """Get (cached) pipeline results for a region."""
    cache_key = f"{region}-{year}"
    if cache_key not in _pipeline_cache:
        print(f"[Cache MISS] Running pipeline for {region} {year}...")
        _pipeline_cache[cache_key] = run_pipeline(region, year=year)
    return _pipeline_cache[cache_key]


# ─────────────────────────────────────────────────────── #
#  STATIC FRONTEND
# ─────────────────────────────────────────────────────── #

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ─────────────────────────────────────────────────────── #
#  API ENDPOINTS
# ─────────────────────────────────────────────────────── #

@app.route("/api/regions")
def api_regions():
    """List all available regions."""
    return jsonify({
        "regions": REGIONS,
        "total": len(REGIONS)
    })


@app.route("/api/sentiment")
def api_sentiment():
    """
    Returns monthly sentiment time-series for one or more regions.
    Query params:
      - region: region name (or 'all' for all regions)
      - year: int (default 2024)
    """
    region = request.args.get("region", "Northeast")
    year = int(request.args.get("year", 2024))

    if region == "all":
        results = {}
        for r in REGIONS:
            data = get_pipeline_data(r, year)
            results[r] = data["monthly_data"]
        return jsonify({
            "year": year,
            "regions": results,
            "message": f"Data for all {len(REGIONS)} regions"
        })

    if region not in REGIONS:
        return jsonify({"error": f"Region '{region}' not found. Available: {REGIONS}"}), 404

    data = get_pipeline_data(region, year)
    return jsonify({
        "region": region,
        "year": year,
        "monthly_data": data["monthly_data"],
        "overall_avg": data["overall_avg"],
        "trend_direction": data["trend_direction"],
        "total_samples": data["total_samples_processed"],
        "spacy_available": data["spacy_available"],
    })


@app.route("/api/chart")
def api_chart():
    """
    Returns a Matplotlib-generated PNG chart.
    Query params:
      - region: comma-separated region names, or 'all'
      - year: int (default 2024)
      - type: 'trend' (default) or 'comparison'
    """
    region_param = request.args.get("region", "Northeast")
    year = int(request.args.get("year", 2024))
    chart_type = request.args.get("type", "trend")

    if chart_type == "comparison":
        summaries = []
        for r in REGIONS:
            data = get_pipeline_data(r, year)
            summaries.append({"region": r, "overall_avg": data["overall_avg"]})
        png_bytes = generate_comparison_bar_chart(summaries)
        return send_file(
            io.BytesIO(png_bytes),
            mimetype="image/png",
            download_name="comparison_chart.png"
        )

    # Trend chart — one or more regions
    if region_param == "all":
        selected_regions = REGIONS
    else:
        selected_regions = [r.strip() for r in region_param.split(",")]
        selected_regions = [r for r in selected_regions if r in REGIONS]

    if not selected_regions:
        return jsonify({"error": "No valid regions specified"}), 400

    region_data = {}
    for r in selected_regions:
        data = get_pipeline_data(r, year)
        region_data[r] = data["monthly_data"]

    region_label = ", ".join(selected_regions) if len(selected_regions) <= 3 else f"{len(selected_regions)} Regions"
    title = f"Mental Health Sentiment Trend — {region_label} ({year})"
    png_bytes = generate_trend_chart(region_data, title=title)

    return send_file(
        io.BytesIO(png_bytes),
        mimetype="image/png",
        download_name="trend_chart.png"
    )


@app.route("/api/resources")
def api_resources():
    """
    Returns resource allocation recommendations for a region.
    Based on sentiment analysis results.
    Query params:
      - region: region name (or 'all')
      - year: int (default 2024)
    """
    region_param = request.args.get("region", "all")
    year = int(request.args.get("year", 2024))

    if region_param == "all":
        target_regions = REGIONS
    else:
        target_regions = [r.strip() for r in region_param.split(",")]
        target_regions = [r for r in target_regions if r in REGIONS]

    table_rows = []
    for r in target_regions:
        data = get_pipeline_data(r, year)
        avg = data["overall_avg"]
        trend = data["trend_direction"]
        samples = data["total_samples_processed"]

        # Determine priority and resource allocation score
        if avg < 40:
            priority = "Critical"
            alloc_score = 95
            counselors = 85
            programs = 12
            budget_pct = 18
        elif avg < 50:
            priority = "High"
            alloc_score = 80
            counselors = 65
            programs = 9
            budget_pct = 15
        elif avg < 60:
            priority = "Moderate"
            alloc_score = 60
            counselors = 45
            programs = 6
            budget_pct = 12
        else:
            priority = "Low"
            alloc_score = 40
            counselors = 30
            programs = 4
            budget_pct = 8

        # Trend modifier
        if trend == "declining":
            alloc_score = min(100, alloc_score + 8)
            priority = "↑ " + priority if priority != "Critical" else priority

        table_rows.append({
            "region": r,
            "avg_sentiment": avg,
            "trend": trend,
            "priority": priority,
            "allocation_score": alloc_score,
            "recommended_counselors": counselors,
            "active_programs": programs,
            "budget_allocation_pct": budget_pct,
            "samples_analyzed": samples,
        })

    # Sort by allocation_score descending (most need first)
    table_rows.sort(key=lambda x: x["allocation_score"], reverse=True)

    return jsonify({
        "year": year,
        "resources": table_rows,
        "total_budget_pct_allocated": sum(r["budget_allocation_pct"] for r in table_rows),
        "total_counselors_needed": sum(r["recommended_counselors"] for r in table_rows),
    })


@app.route("/api/stats")
def api_stats():
    """Dashboard summary statistics across all regions."""
    year = int(request.args.get("year", 2024))
    all_avgs = []
    for r in REGIONS:
        data = get_pipeline_data(r, year)
        all_avgs.append(data["overall_avg"])

    return jsonify({
        "year": year,
        "regions_monitored": len(REGIONS),
        "national_avg_sentiment": round(statistics.mean(all_avgs), 2),
        "highest_region": REGIONS[all_avgs.index(max(all_avgs))],
        "lowest_region": REGIONS[all_avgs.index(min(all_avgs))],
        "highest_score": round(max(all_avgs), 2),
        "lowest_score": round(min(all_avgs), 2),
        "total_samples_processed": sum(
            get_pipeline_data(r, year)["total_samples_processed"] for r in REGIONS
        ),
    })


# ─────────────────────────────────────────────────────── #
#  WARM UP CACHE ON STARTUP
# ─────────────────────────────────────────────────────── #

def warm_cache():
    """Pre-compute all regions at startup to avoid first-request latency."""
    print("[Startup] Warming pipeline cache for all regions...")
    for r in REGIONS:
        get_pipeline_data(r, 2024)
    print("[Startup] Cache ready.")


if __name__ == "__main__":
    warm_cache()
    print("\n" + "=" * 60)
    print("  Mental Health Trend Monitor API")
    print("  Dashboard → http://localhost:5000")
    print("  API Base  → http://localhost:5000/api/")
    print("=" * 60 + "\n")
    app.run(debug=True, port=5000, use_reloader=False)
