# Public Pulse 🇱🇰 : Sri Lankan Civic Intelligence & Political Discourse Analytics Platform

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/FastAPI-1.0.0-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6.svg)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.2-646CFF.svg)](https://vitejs.dev/)
[![Gemini 3.6 Flash](https://img.shields.io/badge/AI-Gemini%203.6%20Flash-4285F4.svg)](https://deepmind.google/technologies/gemini/)
[![Tests](https://img.shields.io/badge/Tests-278%20Passed-success.svg)](#testing--verification)

> **Public Pulse** is an end-to-end research and production platform designed for political discourse analysis, topic modeling, stance detection, and grounded AI synthesis across Sri Lankan broadcast TV and digital media channels. It processes multilingual and code-switched user comments (Sinhala, Singlish, Tamil, and English) scraped from YouTube talk shows and news broadcasts.

---

## 📋 Table of Contents

- [Executive Summary](#-executive-summary)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Taxonomy & ML Classifier Cascade](#-taxonomy--ml-classifier-cascade)
- [Grounded AI & Faithfulness Engine](#-grounded-ai--faithfulness-engine)
- [Project Directory Structure](#-project-directory-structure)
- [Installation & Setup](#-installation--setup)
- [Running the Application](#-running-the-application)
- [API Reference](#-api-reference)
- [Testing & Verification](#-testing--verification)
- [License & Disclaimer](#-license--disclaimer)

---

## 🎯 Executive Summary

Public debate around televised political talk shows (such as *Hiru Salakuna*, *Sirasa Satana*, *Ada Derana 360*, etc.) forms a vital pulse of Sri Lanka's civic democracy. **Public Pulse** automates the collection, noise filtering, thematic classification, stance orientation detection, and AI-grounded policy synthesis from public comments.

The system features:
1. **A 3-Stage Cascading Neural Classifier**: Powered by fine-tuned `xlm-roberta-base` models designed specifically for code-switched Indic/South Asian text.
2. **FastAPI Server-Side Analytics**: Ultra-fast RESTful aggregation endpoints backed by a normalized PostgreSQL / Supabase schema.
3. **Grounded AI Intelligence**: Automatic political discourse synthesis powered by **Google Gemini 3.6 Flash** with 100% evidence-backed citations.
4. **Automated Faithfulness Auditor**: Natural Language Inference (NLI) claim verification engine calculating grounding and entailment scores.
5. **Modern GA4 & Apple-inspired Dashboard**: High-contrast, clean React 19 + TypeScript + Vite web dashboard for interactive exploration.

---

## ⚡ Key Features

- 🧹 **Layer 1 Noise Filtering**: Automatically filters out spam, self-promotion, unparseable emojis, and gibberish (`NOISE`), isolating usable civic comments (`VALID`).
- 🏷️ **Layer 2 Macro-Topic Classification**: Categorizes valid discourse into 5 primary policy domains:
  - `TOPIC_ECON_SERV` — Economics, Living Costs, Taxes, Fuel, Tariffs, & Public Services.
  - `TOPIC_GOV` — Governance, Executive Actions, Cabinet, & Political Reform.
  - `TOPIC_LAW` — Law & Justice, Judiciary, Anti-Corruption, & Fundamental Rights.
  - `TOPIC_MEDIA` — Press Freedom, Media Regulation, & Journalistic Ethics.
  - `TOPIC_FOR` — Foreign Relations, Bilateral Agreements, IMF Programs, & Maritime Diplomacy.
- ⚖️ **Layer 4 Stance Orientation**: Measures commenter sentiment/orientation toward subjects:
  - `STANCE_CRIT` — Critical / Skeptical / Dissatisfied.
  - `STANCE_NEUT` — Neutral / Procedural / Informational.
  - `STANCE_SUPP` — Supportive / Approved / Favorable.
- 🤖 **Interactive Data Collection Wizard**: Trigger live YouTube extraction for specific target channels and programs directly from the dashboard.
- 🛡️ **Faithfulness & NLI Entailment**: Every AI summary claim is verified against raw comment citations to prevent hallucinations.
- 📊 **Dynamic Heatmaps & Cross-Tabulations**: Explore Topic × Stance heatmaps, volume trend time-series, and channel-by-channel comparison matrices.

---

## 🏗️ System Architecture

```
                               ┌──────────────────────────────────────────────┐
                               │       YouTube Data API v3 Scraper            │
                               └──────────────────────┬───────────────────────┘
                                                      │ (Raw Text)
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │    Text Preprocessing & Normalizer           │
                               │      - clean_text() & deduplication          │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │     Cascade Neural Classifier Engine         │
                               │  Layer 1 (Utility) ──> Layer 2 & Layer 4     │
                               └──────────────────────┬───────────────────────┘
                                                      │ (Predictions & Metadata)
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │       PostgreSQL Database (Supabase)         │
                               │ (channels, programs, videos, comments, etc.) │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │           FastAPI Backend Service            │
                               │        http://localhost:8000/api/v1          │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │      React + TypeScript Web Dashboard        │
                               │           http://localhost:5173              │
                               └──────────────────────────────────────────────┘
```

---

## 🧠 Taxonomy & ML Classifier Cascade

The cascade inference engine ([`src/public_pulse/inference/cascade.py`](file:///D:/Final%20project/New%20folder/public-pulse/src/public_pulse/inference/cascade.py)) evaluates comments sequentially:

```
                      ┌────────────────────────┐
                      │    Input Comment       │
                      └───────────┬────────────┘
                                  │
                                  ▼
                      ┌────────────────────────┐
                      │ Layer 1: Utility Model │
                      └───────────┬────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 │                                 │
           [VALID Comment]                  [NOISE Comment]
                 │                                 │
        ┌────────┴────────┐                        ▼
        │                 │                 Mark status = noise_exit
        ▼                 ▼                 (Stop further scoring)
┌───────────────┐ ┌───────────────┐
│ Layer 2 Model │ │ Layer 4 Model │
│ (Macro Topic) │ │ (Stance)      │
└───────────────┘ └───────────────┘
```

*Note on Architecture History*: The sub-issue layer (formerly Layer 3) was permanently removed as a documented research-scope decision due to sparse label distribution (~7% coverage across 60+ classes). The official layer numbering (Layer 1, Layer 2, Layer 4) is intentionally preserved to maintain continuity with published research records.

---

## 🤖 Grounded AI & Faithfulness Engine

Public Pulse implements a complete RAG (Retrieval-Augmented Generation) pipeline for civic intelligence:

1. **Evidence Retrieval**: Executes BM25 / hybrid filtering over scored database comments to assemble bounded `EvidenceSets`.
2. **Gemini 3.6 Flash Synthesis**: Calls the official Google GenAI SDK to generate structured summaries, core empirical findings, and qualitative interpretations.
3. **Automated Faithfulness Audit**: An NLI cross-encoder model evaluates every generated claim against cited evidence, outputting:
   - **Grounding Score**: Proportion of claims strictly entailed by cited evidence.
   - **Claim Support Rate**: Entailment score across individual findings.
   - **Verification Badges**: Displayed directly in the dashboard UI.

---

## 📁 Project Directory Structure

```
public-pulse/
├── api/                             # FastAPI Backend Service
│   ├── main.py                      # FastAPI app entrypoint & CORS middleware
│   ├── deps.py                      # DB Session dependencies
│   ├── routes/                      # API endpoint routers (analytics, insights, catalog, etc.)
│   ├── schemas/                     # Pydantic schemas & response contracts
│   └── services/                    # Server-side business logic & aggregation services
├── dashboard/                       # Modern React 19 + Vite Dashboard
│   ├── src/
│   │   ├── api/                     # Centralized API client & HTTP wrappers
│   │   ├── components/              # UI Cards, Metric Groups, Heatmaps, & Charts
│   │   ├── context/                 # FilterContext (global date/channel/program scope)
│   │   ├── features/                # Page features (Overview, Insights, Sources, Volume, etc.)
│   │   ├── lib/                     # Constants, Color Maps, & Number Formatters
│   │   └── types/                   # TypeScript interfaces matching API schemas
│   ├── package.json                 # Node dependencies (@tailwindcss/vite, recharts, etc.)
│   └── vite.config.ts               # Vite configuration & proxy settings
├── configs/                         # Model & Pipeline configuration files
├── data/                            # Dataset directories (raw, processed, splits, golden_sample)
├── docs/                            # Research & technical documentation (taxonomy, architecture, schema)
├── models/                          # Trained XLM-RoBERTa model configs & label maps
├── scripts/                         # CLI execution & pipeline scripts
│   ├── scrape_live.py               # Live YouTube extraction runner
│   ├── scrape_historical.py         # Historical batch scraper
│   ├── clean_data.py                # Preprocessing pipeline script
│   └── validate_data.py             # Dataset schema validator
├── src/public_pulse/                # Core Python Package
│   ├── database/                    # SQLAlchemy models, sessions, & repository queries
│   ├── evidence/                    # EvidenceSet retrieval engine
│   ├── extraction/                  # YouTube Data API scraper
│   ├── inference/                   # Cascade neural inference pipeline
│   ├── insight/                     # Gemini 3.6 Flash insight generator
│   └── verification/                # NLI Faithfulness verification engine
└── tests/                           # Comprehensive Pytest test suite (278 passing tests)
```

---

## ⚙️ Installation & Setup

### Prerequisites
- **Python**: `3.11.x`
- **Node.js**: `v18.x` or higher
- **Package Manager**: `npm` or `bun`
- **Database**: PostgreSQL (Supabase pooler recommended)

### 1. Clone & Python Virtual Environment
```bash
git clone https://github.com/your-org/public-pulse.git
cd public-pulse

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows PowerShell
# source venv/bin/activate    # Linux / macOS

# Install package and dependencies
pip install -e ".[dev]"
```

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://user:password@db.supabase.co:5432/postgres
YOUTUBE_API_KEY=your_youtube_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
DASHBOARD_ORIGIN=http://localhost:5173,http://127.0.0.1:5173
```

### 3. Dashboard Installation
```bash
cd dashboard
npm install
```

---

## 🚀 Running the Application

### Option A: Running Backend & Frontend Concurrently

1. **Start the FastAPI Backend Server**:
   ```powershell
   # From root directory:
   .\venv\Scripts\python.exe -m uvicorn api.main:app --port 8000 --host 127.0.0.1
   ```
   *Backend interactive OpenAPI docs will be available at:* [`http://localhost:8000/api/docs`](http://localhost:8000/api/docs)

2. **Start the React Web Dashboard**:
   ```powershell
   # From dashboard/ directory:
   cd dashboard
   npm run dev -- --port 5173
   ```
   *Dashboard will be accessible at:* [`http://localhost:5173`](http://localhost:5173)

---

## 📡 API Reference

The FastAPI backend exposes the following primary endpoints under `/api/v1`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Application and database health check |
| `GET` | `/analytics/overview` | Executive KPI cards (total comments, valid rate, noise rate, episode count) |
| `GET` | `/analytics/topics` | Layer 2 macro-topic distribution percentages and comment counts |
| `GET` | `/analytics/stances` | Layer 4 stance orientation distribution (Critical, Neutral, Supportive) |
| `GET` | `/analytics/topic-stance-matrix` | 5×3 cross-tabulation matrix of topics by stance orientation |
| `GET` | `/analytics/volume-over-time` | Daily/weekly volume trends of valid comments vs. filtered noise |
| `GET` | `/analytics/episodes` | Per-episode analytical breakdown table with top topics and stance bars |
| `GET` | `/channels` | List all monitored YouTube channels |
| `GET` | `/programs` | List all monitored political talk shows and broadcast programs |
| `GET` | `/insights` | List all generated Grounded AI insights |
| `GET` | `/insights/{id}` | Retrieve full details, findings, and evidence for a specific insight |
| `GET` | `/insights/{id}/verification` | Retrieve NLI claim verification and faithfulness report |
| `POST`| `/collection/run` | Trigger live YouTube data collection for selected channel/programs |

---

## 🧪 Testing & Verification

The project includes a thorough test suite covering unit, integration, and API contract tests.

### Run All Backend Tests
```bash
.\venv\Scripts\python.exe -m pytest tests/
```
*Expected Output:*
```
================= 278 passed, 6 warnings in 73.59s =================
```

### Verify Frontend TypeScript Build
```bash
cd dashboard
npm run build
```
*Expected Output:*
```
✓ 2026 modules transformed.
✓ built in 4.17s
```

---

## 📜 License & Disclaimer

**Political Neutrality Disclaimer**: Stance orientation metrics represent the contextual framing of user comments toward specific subject matters in public broadcasts. They do not represent political affiliation, personal identity, or endorsement of any political party or entity.
