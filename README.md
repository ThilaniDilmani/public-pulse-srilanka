# Public Pulse 🇱🇰

**A civic-intelligence platform that listens to how Sri Lanka actually talks about politics — in Sinhala, Singlish, and English, all at once.**

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Status](https://img.shields.io/badge/status-in%20development-yellow)
![License](https://img.shields.io/badge/license-TBD-lightgrey)

---

## What is Public Pulse?

Every day, thousands of Sri Lankans react to the news — in the comment sections and live chats of major TV talk shows and independent political YouTube channels. That conversation is public, huge, and almost entirely unread by anyone trying to understand what the country actually thinks.

**Public Pulse listens to it.** It collects public YouTube comments and live-chat messages from major Sri Lankan political and media programs, and uses machine learning to understand what people are talking about, how they feel about it, and — critically — whether they're being genuinely critical or sarcastically critical, a distinction most sentiment tools miss entirely.

The result is meant to be a live, honest dashboard: a way for citizens, journalists, researchers, and policymakers to see public reaction to real events (a fuel price hike, a corruption allegation, an election announcement) without needing to scroll through tens of thousands of comments themselves.

**In plain terms:** it's a way of taking the temperature of public opinion by listening to what people are already saying, in the language they actually speak — not a formal survey, not a curated poll, just the real, messy, funny, angry public conversation, made readable.

---

## Table of Contents

- [Why This Matters](#why-this-matters)
- [How It Works](#how-it-works)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Dataset & Classification Taxonomy](#dataset--classification-taxonomy)
- [Contributors](#contributors)

---

## Why This Matters

- **Gives citizens a transparent voice.** Instead of politicians or media companies guessing what the public thinks, Public Pulse aggregates real, unfiltered public reaction into something readable.
- **Supports accountability.** Tracking public reaction to specific policies (fuel prices, taxes, healthcare, education) makes the real-world impact of decisions visible, not just assumed.
- **Cuts through noise.** By filtering spam and organizing discussion by topic, it helps journalists and researchers find the actual signal in an otherwise unmanageable volume of comments.
- **Takes code-switching seriously.** Most Sri Lankan political commentary mixes Sinhala, English, and Singlish (romanized Sinhala) in the same sentence — Public Pulse is built specifically to understand that, rather than treating it as noise.

---

## How It Works

At a high level, the system has four stages:

1. **Collect** — Python scripts using the YouTube Data API v3 gather comments and live-chat messages from 8+ Sri Lankan political/media channels, on a scheduled, automated basis.
2. **Classify** — Each comment passes through a 4-layer classification pipeline, built on independently fine-tuned [XLM-RoBERTa](https://huggingface.co/xlm-roberta-base) models:
   - **Layer 1 — Utility:** Is this a real comment, or spam/noise?
   - **Layer 2 — Topic:** What's it about? (economy, governance, public services, law, foreign affairs, media)
   - **Layer 3 — Stance & Sarcasm:** Is the person supportive, neutral, directly critical, or sarcastically critical?
3. **Store** — Classified results are stored in a PostgreSQL database (Supabase/Neon).
4. **Display** — A dashboard (in development) surfaces sentiment trends, topic breakdowns, and program-by-program comparisons for anyone to explore.

For the full technical architecture, see [`docs/architecture.md`](docs/architecture.md).
---

## Tech Stack

| Layer | Technology |
|---|---|
| Data collection | Python, YouTube Data API v3 |
| ML / NLP | [XLM-RoBERTa](https://huggingface.co/xlm-roberta-base) (Hugging Face Transformers), PyTorch |
| Database | PostgreSQL (Supabase / Neon) |
| Backend API | FastAPI, deployed on Hugging Face Spaces |
| Dashboard | Streamlit / Vercel |
| Automation | GitHub Actions (scheduled scraping, tests, deployment) |
| Notebooks | Jupyter |

### Resource & Dependency Versions

| Requirement | Version |
|---|---|
| **Python** | **3.11+** |
| transformers | 4.53.0 |
| torch | 2.2+ (verified against 2.13.x in Colab training environment) |
| datasets | 2.19+ |
| accelerate | 0.30+ |
| sentencepiece | 0.2+ |
| scikit-learn | 1.4+ |
| pandas | 2.2+ |
| numpy | 1.26+ |
| fastapi | 0.111+ |
| uvicorn | 0.29+ |
| pydantic | 2.7+ |
| sqlalchemy | 2.0+ |
| psycopg2-binary | 2.9+ |
| streamlit | 1.35+ |
| pyyaml | 6.0+ |
| python-dotenv | 1.0+ |
| pytest | 8.2+ |

Full pinned list: [`requirements.txt`](requirements.txt) / [`pyproject.toml`](pyproject.toml).

> **Note on `transformers==4.53.0`:** this exact version is pinned rather than left as a floor (`>=`), because Google Colab's preinstalled `torch` version has caused dependency conflicts (specifically with `torchvision`) at other `transformers` versions during training. If you hit an import error mentioning `torchvision::nms` in Colab, see the troubleshooting note in `notebooks/06_layer1_utility/02_training.ipynb`.

---

## Repository Structure

```text
public-pulse/
├── data/                # raw -> interim -> processed -> golden_sample -> splits (gitignored except structure)
├── notebooks/           # one clear purpose per notebook, numbered by pipeline stage
├── src/public_pulse/    # all reusable code (data, preprocessing, models, training, inference, database)
├── models/              # per-layer config + label maps; trained checkpoints hosted on Hugging Face Hub
├── results/             # EDA plots, training curves, confusion matrices, classification reports
├── configs/             # YAML configs per layer — no secrets
├── api/                 # FastAPI service
├── dashboard/           # Streamlit dashboard (independent of training code)
├── deployment/          # Docker + Hugging Face Spaces config
├── docs/                # architecture, taxonomy, and database schema documentation
└── .github/workflows/   # scheduled scraper, tests, deployment
```

Full architecture and folder-by-folder rationale: [`docs/architecture.md`](docs/architecture.md).

---

## Getting Started

### Prerequisites
- Python 3.10 or higher
- Git
- (Optional but recommended for training notebooks) Access to a GPU — e.g. [Google Colab](https://colab.research.google.com/)'s free tier

### Setup

```bash
# Clone the repository
git clone https://github.com/<org-or-owner>/public-pulse.git
cd public-pulse

# Install dependencies
pip install -e ".[dev]"
# or, if using requirements.txt directly:
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# then fill in DATABASE_URL, YOUTUBE_API_KEY, etc.
```

### Running the notebooks

Notebooks are numbered and meant to be run in order within each `notebooks/0X_*/` folder — for example, Layer 1's pipeline:

```text
notebooks/06_layer1_utility/
├── 01_data_preparation.ipynb   # cleans, documents, and splits the Golden Sample
├── 02_training.ipynb            # fine-tunes XLM-RoBERTa (GPU strongly recommended)
└── 03_evaluation.ipynb          # final held-out test-set evaluation
```

Each notebook includes a **Handover Notes** section at the end explaining exactly what the next notebook needs, so any contributor can pick up the pipeline without needing to ask.

---

## Dataset & Classification Taxonomy

Public Pulse uses a 3-layer classification system, applied to each comment in sequence:

```text
Raw Comment
    ↓
Layer 1 — Utility (VALID / NOISE)
    ↓
Layer 2 — Macro Topic (economy, governance, services, law, foreign affairs, media)
    ↓
Layer 4 — Stance & Sarcasm (supportive / neutral / directly critical / sarcastically critical)
```

Full label definitions and reasoning: [`docs/taxonomy.md`](docs/taxonomy.md). Database schema: [`docs/database_schema.md`](docs/database_schema.md).

---

## Contributors

This is a group project built and maintained by:

| Name | GitHub |
|---|---|
| Thilani | [@thilani](https://github.com/ThilaniDilmani) |
| Achira | [@achira](https://github.com/achira-sadharanga) |
| Aadhil | [@aadhil](https://github.com/AadhilAslam88) |
| Thrithwaka | [@thrithwaka](https://github.com/Thrithwaka) |
| Malith | [@malith](https://github.com/sankalpams) |

> ⚠️ **Before publishing this README:** the GitHub usernames above are placeholders and almost certainly do not point to the correct profiles. Each contributor should replace their own link with their real GitHub profile URL (e.g. `https://github.com/actual-username`) before this goes live — please don't leave these as-is, since they may currently point to unrelated real accounts.

---

## Acknowledgments

Built as part of an academic/research project on multilingual NLP for low-resource, code-switched languages, using [XLM-RoBERTa](https://arxiv.org/abs/1911.02116) (Conneau et al.) as the multilingual backbone.
