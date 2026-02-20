# Mental Health Trend Monitor

A data-driven policy dashboard that simulates an NLP sentiment-analysis pipeline 
(spaCy + NLTK VADER) on anonymized mental health text data and visualizes regional 
trends using Matplotlib.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web Server | Flask + Flask-CORS |
| NLP Tokenizer | spaCy (`en_core_web_sm`) |
| Sentiment Analysis | NLTK VADER |
| Chart Rendering | Matplotlib (server-side PNG) |
| Frontend | Vanilla HTML / CSS / JS |

---

## Quick Start

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download NLP Models

```bash
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('vader_lexicon')"
```

### 3. Start the Server

```bash
python backend/app.py
```

### 4. Open the Dashboard

Navigate to **http://localhost:5000** in your browser.

---

## Project Structure

```
MS Evelate/
├── backend/
│   ├── app.py              # Flask API server + static file serving
│   ├── data_pipeline.py    # spaCy NLP + NLTK VADER pipeline
│   ├── data_generator.py   # Anonymized synthetic text corpus
│   └── chart_generator.py  # Matplotlib chart rendering
├── frontend/
│   ├── index.html          # Dashboard HTML
│   ├── styles.css          # Blue-teal design system
│   └── app.js              # Frontend logic + API integration
└── requirements.txt
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/regions` | List all available regions |
| `GET /api/sentiment?region=X` | Monthly sentiment time-series |
| `GET /api/chart?region=X&type=trend` | Matplotlib PNG chart |
| `GET /api/chart?type=comparison` | Regional comparison bar chart |
| `GET /api/resources?region=X` | Resource allocation table data |
| `GET /api/stats` | National summary statistics |

## Features

- **Region Selection** sidebar with per-region sentiment scores
- **Matplotlib trend line charts** served as PNG from the backend  
- **NLTK VADER sentiment** with spaCy-enhanced negation detection
- **Resource Allocation table** — sortable, searchable, CSV-exportable
- **NLP Pipeline status** panel showing component availability
- **Dark blue-teal design** optimized for professional policy use
