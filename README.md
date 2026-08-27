# Public Pulse

Civic-intelligence platform analyzing public sentiment, topics, and
political stance in Sri Lankan TV and digital media discourse (YouTube
comments/live chats, 14 target channels, Sinhala/Singlish/English
code-switched text).

## Structure

- `data/` -- raw -> interim -> processed -> golden_sample -> splits
- `notebooks/` -- one purpose per notebook, numbered by pipeline stage
- `src/public_pulse/` -- all reusable code (data, preprocessing, models, training, inference, database)
- `models/` -- config + label_map per layer; checkpoints pushed to Hugging Face Hub
- `results/` -- generated plots, metrics, reports (decoupled from notebooks)
- `configs/` -- YAML configs per layer, no secrets
- `api/` -- FastAPI service, deployed to Hugging Face Spaces
- `dashboard/` -- Streamlit dashboard, reads only from Postgres/API
- `deployment/` -- Docker + Hugging Face Spaces config
- `.github/workflows/` -- scraper cron, tests, deploy

See `docs/architecture.md`, `docs/taxonomy.md`, and `docs/database_schema.md`
for full details.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env   # fill in DATABASE_URL, YOUTUBE_API_KEY, HF_TOKEN
pytest tests/
```

## Four-layer taxonomy

1. Utility (spam/noise gatekeeper)
2. Macro topic (economy, governance, services, law, foreign, media)
3. Fine-grained sub-issue
4. Pragmatic stance & sarcasm

Each layer is an independently fine-tuned `xlm-roberta-base` checkpoint,
run sequentially via `src/public_pulse/inference/cascade.py`.
