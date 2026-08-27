# Public Pulse — Repository & System Architecture

Philosophy: **Industry Best Practices + Research Reproducibility + Student Practicality + Free-Tier Cloud.**
Nothing enterprise-grade for its own sake. Every folder, tool, and workflow below exists because Public Pulse's specific pipeline (14-source scrape → 4-layer modular XLM-RoBERTa cascade → Postgres → FastAPI → dashboard, all on free tiers) actually needs it.

---

## A. Recommended Repository Tree

```text
public-pulse/
│
├── data/
│   ├── raw/                    # untouched scraped exports (per source, per date)
│   ├── interim/                # deduped, validated, not yet cleaned
│   ├── processed/               # cleaned, ready for annotation/training
│   ├── annotations/             # manual labels, IAA files, label guidelines
│   ├── golden_sample/           # the ~2,000-row annotated gold set
│   └── splits/                  # train/ val/ test/ per layer
│       ├── layer1/
│       ├── layer2/
│       ├── layer3/
│       └── layer4/
│
├── notebooks/
│   ├── 01_data_collection/
│   ├── 02_data_quality/
│   ├── 03_data_preprocessing/
│   ├── 04_eda/
│   ├── 05_annotation_analysis/
│   ├── 06_layer1_utility/
│   ├── 07_layer2_topic/
│   ├── 08_layer3_subissue/
│   ├── 09_layer4_stance/
│   ├── 10_model_comparison/
│   ├── 11_error_analysis/
│   └── 12_final_inference/
│
├── src/
│   └── public_pulse/
│       ├── data/                # loading, dedup, validation, cleaning
│       ├── preprocessing/       # normalization, code-switch handling, tokenization
│       ├── labels/              # label maps, taxonomy versioning
│       ├── models/              # model wrappers per layer (shared base class)
│       ├── training/            # trainer, callbacks, metrics
│       ├── evaluation/          # confusion matrices, reports
│       ├── inference/           # cascade runner (layer1→2→3→4)
│       ├── database/            # SQLAlchemy models, repository/query layer
│       ├── pipeline/            # orchestration: scrape→clean→score→store
│       └── utils/                # config loading, logging, io helpers
│
├── models/
│   ├── layer1_utility/
│   │   ├── config.json
│   │   ├── label_map.json
│   │   └── checkpoints/         # gitignored, or DVC/HF Hub pointer
│   ├── layer2_topic/
│   ├── layer3_subissue/
│   └── layer4_stance/
│
├── results/
│   ├── eda/
│   ├── training_curves/
│   ├── confusion_matrices/
│   ├── classification_reports/
│   ├── model_comparison/
│   ├── error_analysis/
│   └── experiment_logs/
│
├── configs/
│   ├── base.yaml
│   ├── layer1.yaml
│   ├── layer2.yaml
│   ├── layer3.yaml
│   ├── layer4.yaml
│   └── deployment.yaml
│
├── tests/
│   ├── test_data_cleaning.py
│   ├── test_deduplication.py
│   ├── test_preprocessing.py
│   ├── test_label_validation.py
│   ├── test_inference.py
│   ├── test_database.py
│   └── test_api.py
│
├── scripts/
│   ├── scrape_historical.py
│   ├── scrape_live.py
│   ├── clean_data.py
│   ├── validate_data.py
│   ├── build_golden_sample.py
│   └── run_inference.py
│
├── api/
│   ├── main.py
│   ├── routes/
│   ├── schemas/
│   └── services/
│
├── dashboard/
│   ├── app.py
│   └── components/
│
├── deployment/
│   ├── docker/
│   │   ├── Dockerfile.api
│   │   └── .dockerignore
│   └── huggingface/
│       └── README.md            # HF Spaces metadata
│
├── docs/
│   ├── architecture.md
│   ├── taxonomy.md
│   └── database_schema.md
│
├── .github/
│   └── workflows/
│       ├── scraper.yml
│       ├── tests.yml
│       └── deploy_api.yml
│
├── .env.example
├── .gitignore
├── .dvcignore                   # only if DVC adopted
├── pyproject.toml
├── README.md
└── Dockerfile                    # convenience root, mirrors deployment/docker
```

---

## B. Folder-by-Folder Explanation

**`data/`** — Exists to separate raw evidence from derived artifacts, which is the single most important reproducibility rule in ML. `raw/` is write-once — scrapers append, nothing else touches it. `interim/` holds deduped/validated-but-uncleaned data. `processed/` is what preprocessing/annotation notebooks read from. `golden_sample/` is your 2,000-row hand-labeled set — treat it as precious, back it up separately. Committed to Git: **no** (except tiny schema/sample files) — real data goes to `.gitignore`, and either stays in Postgres (source of truth) or is versioned with DVC if you want file-level history.

**`notebooks/`** — One purpose per notebook, numbered by pipeline stage so the lifecycle reads top to bottom. Not committed with outputs (strip via `nbstripout` or clear before commit) — notebook diffs with embedded images/outputs are unreviewable in Git.

**`src/public_pulse/`** — All reusable logic. This is what notebooks, scripts, and the API all import from, so cleaning logic is written once. Committed: **yes**, always.

**`models/`** — One directory per layer, each self-contained: config, label map, checkpoint. Trained weights (checkpoints/) are **not** committed — see Section E.

**`results/`** — Generated plots/metrics/reports, decoupled from notebooks so re-running a notebook doesn't silently overwrite history you wanted to compare against. Small plots/JSON metrics: commit. Large artifacts (many checkpoints' worth of prediction dumps): gitignore.

**`configs/`** — Central place for hyperparameters, label maps, paths — never hardcoded in notebooks or `src/`. Committed: yes (no secrets).

**`tests/`** — Practical coverage only: the things that silently break a pipeline (dedup logic, label validation, inference contract, DB writes) — not exhaustive unit tests of every function.

**`scripts/`** vs **`src/`** — Scripts are thin CLI entry points ("do the thing end to end"); `src/` is the library of functions scripts call. A script should be almost all imports plus argument parsing, no real logic.

**`api/`** — Kept as its own top-level folder rather than nested in `src/`, because it's a deployable service with its own lifecycle (Docker image, HF Spaces deploy) distinct from the training codebase, even though it imports from `src/public_pulse/inference`.

**`dashboard/`** — Deliberately has zero import dependency on `src/` training code — it only talks to Postgres or the API. This keeps the dashboard deployable and iterable independently of anything ML-related.

**`deployment/`** — Isolates all container/hosting config so `docker build` and HF Spaces config aren't scattered through the repo root.

---

## C. Notebook Architecture & Lifecycle

```text
01_data_collection/     → sanity-check scraper output, inspect API responses
02_data_quality/        → missing values, duplicates, malformed rows
03_data_preprocessing/  → normalization decisions, tokenizer behavior on Sinhala/Singlish
04_eda/                 → volume by channel, comment length, emoji frequency, language mix
05_annotation_analysis/ → inter-annotator agreement, label distribution in golden sample
06-09_layerN_*/         → one notebook family per layer: train, tune, evaluate
10_model_comparison/    → cross-layer/cross-checkpoint comparison
11_error_analysis/      → misclassifications, confusion patterns, hard examples
12_final_inference/     → run the full 4-layer cascade end-to-end on a sample
```

Lifecycle rule: a notebook is for **exploration and one-off analysis**. The moment code from a notebook gets called a second time (by another notebook, a script, or the API), it moves into `src/`. Notebooks should shrink over the project's life as more logic migrates out — a healthy sign, not a loss of work.

---

## D. Notebook vs `src/`

| Notebook | `src/` |
|---|---|
| Visualizations, hypothesis tests | Data loading, cleaning, validation |
| Model comparison, ad hoc analysis | Tokenization, dataset construction |
| Temporary exploration | Training loop, evaluation metrics |
| Single-run experiments | Inference (the cascade runner) |
| | Database access layer, API service logic |

Refactor rule of thumb: if you copy-paste a cell into a second notebook, stop — extract it into `src/public_pulse/<module>/` immediately and import it back.

---

## E. `src/` Architecture — Shared Components for 4 Independent Layers

```text
src/public_pulse/
├── data/           # shared: load_raw(), dedup(), validate_schema()
├── preprocessing/  # shared: normalize_text(), handle_codeswitch(), tokenize()
├── labels/         # shared: LabelMap class, taxonomy versioning per layer
├── models/
│   ├── base.py     # BaseClassifier: load/save/predict contract
│   ├── layer1.py   # UtilityClassifier(BaseClassifier)
│   ├── layer2.py   # TopicClassifier(BaseClassifier)
│   ├── layer3.py   # SubIssueClassifier(BaseClassifier)
│   └── layer4.py   # StanceClassifier(BaseClassifier)
├── training/       # shared Trainer class, layer-specific config injected
├── evaluation/      # shared metrics.py (works for any layer given label_map)
├── inference/
│   └── cascade.py  # runs layer1→2→3→4 sequentially, respects early-exit
├── database/       # SQLAlchemy models + repository functions
└── pipeline/       # orchestrates scrape→clean→score→store end-to-end
```

**Decoupling principle:** the four layers share *infrastructure* (a common `BaseClassifier`, common tokenization, common metrics functions, common DB writer) but never share *state* — each layer's model, label map, and checkpoint are independent artifacts. This is what "modular, not multi-task" means at the code level: `cascade.py` is the only file that knows all four layers exist; each `layerN.py` only knows its own labels.

---

## F. Four-Layer Model Organization

```text
models/
├── layer1_utility/{config.json, label_map.json, checkpoints/}
├── layer2_topic/{...}
├── layer3_subissue/{...}
└── layer4_stance/{config.json, label_map.json, checkpoints/}
```

Trained checkpoints (often 400MB–1.1GB each) should **not** be committed to GitHub — GitHub has a 100MB hard file limit and repo-bloat problems well before that. Recommended alternative: push checkpoints to the **Hugging Face Hub** (free, designed for exactly this, and it's already where your FastAPI inference space lives — one less integration to build) or use **DVC with a free remote** (e.g., a Google Drive or free-tier S3-compatible bucket) if you want Git-linked versioning of weights. For a student project, Hugging Face Hub is simpler and sufficient — commit only `config.json` and `label_map.json` to Git, reference the Hub repo ID in `configs/layerN.yaml`.

---

## G. Results & Experiment Artifacts

| Artifact | Commit? |
|---|---|
| Small PNG/SVG plots, EDA summaries | Yes |
| Classification reports (JSON/CSV), F1/precision/recall tables | Yes |
| Confusion matrices (small images) | Yes |
| Training curves (small) | Yes |
| Raw prediction dumps, large error-analysis CSVs | No — gitignore, keep locally or in DB |
| Full experiment logs (verbose) | No — gitignore, or push to MLflow if adopted later |

---

## H. Database Architecture

Code home: `src/public_pulse/database/` — SQLAlchemy models in `models.py`, query/repository functions in `repository.py`, raw SQL migrations in `database/migrations/` (or Alembic if you want managed migrations).

Conceptual schema:

```text
programs (id, name, platform, channel_url)
videos (id, program_id FK, youtube_video_id, title, published_at, is_live)
comments (id, video_id FK, author_hash, text_raw, posted_at, scraped_at)
annotations (id, comment_id FK, annotator, layer, label, created_at)
layer_predictions (id, comment_id FK, layer, label, confidence, model_version_id FK, predicted_at)
model_versions (id, layer, checkpoint_ref, trained_at, metrics_json)
processing_runs (id, run_type, started_at, finished_at, status, rows_processed)
```

Deliberately not over-engineered: no separate "users" table (dashboard is read-only/public), no event-sourcing, no soft-delete framework — just enough normalization to avoid duplicate scraping and to trace every prediction back to the model version that produced it.

---

## I. API Architecture

```text
api/
├── main.py         # FastAPI app instantiation
├── routes/         # /comments, /sentiment, /topics, /programs
├── schemas/         # Pydantic request/response models
└── services/         # thin layer calling src/public_pulse/inference + database
```

Kept as a top-level folder, not inside `src/`, because it's a deployable unit (its own Docker image, its own HF Space) with a different release cadence than the ML codebase — but it imports `src/public_pulse` as a dependency rather than duplicating logic. Given the batch-scoring architecture discussed earlier, most routes should be **read-only queries against pre-scored Postgres rows**, not on-demand model inference.

---

## J. Dashboard Architecture

```text
dashboard/
├── app.py
└── components/     # sentiment_tracker.py, topic_meter.py, program_compare.py, sarcasm_view.py
```

Talks only to Postgres (directly, or via the FastAPI `/comments` etc. endpoints) — never imports training code. This means the dashboard can be redeployed, redesigned, or even rewritten in a different framework without touching the ML pipeline at all.

---

## K. Testing Architecture

Practical, not exhaustive:

```text
test_data_cleaning.py      # normalization doesn't corrupt Sinhala/Singlish text
test_deduplication.py      # same video isn't re-scraped/re-inserted
test_preprocessing.py      # tokenizer handles code-switched samples correctly
test_label_validation.py   # predicted labels are always in the taxonomy's allowed set
test_inference.py          # cascade produces one label per layer per comment, respects early-exit
test_database.py           # repository functions read/write expected schema
test_api.py                # routes return expected shape/status codes
```

Run via `pytest`, wired into `.github/workflows/tests.yml` on every push/PR.

---

## L. MLOps Architecture

| Now (required) | Useful later | Not necessary yet |
|---|---|---|
| Config files (YAML) per layer | MLflow experiment tracking | Model registry service |
| Label map versioning in `labels/` | DVC for large dataset/checkpoint versioning | Kubernetes / orchestration |
| Manual model_versions table in Postgres | CI/CD auto-deploy on merge to main | Feature store |
| Git for code | Automated retraining triggers | Multi-region deployment |

Reasoning: at 40k comments and 4 single-purpose classifiers, a spreadsheet-simple `model_versions` table plus disciplined config files gives you 90% of reproducibility for near-zero setup cost. MLflow/DVC become worth the overhead once you're iterating on many checkpoint variants per layer or collaborating with other people.

---

## M–N. Git/GitHub Strategy & GitHub Actions

Minimum practical workflow set:

- **`scraper.yml`** — scheduled (cron), runs `scripts/scrape_historical.py`, writes to Postgres. This is the only workflow that should run frequently.
- **`tests.yml`** — on push/PR, runs `pytest`. Fast, cheap, catches breakage before merge.
- **`deploy_api.yml`** — on push to `main` (or manual dispatch), rebuilds/pushes the FastAPI Docker image to Hugging Face Spaces.

Deliberately **not** included yet: a live-chat capture workflow (doesn't fit cron's execution model — see below), an automated retraining workflow (retraining should stay a manual, reviewed decision at this project's stage), and a Docker-build-on-every-commit workflow (wasteful; only build on deploy).

**Live-chat caveat carried over from earlier discussion:** GitHub Actions scheduled jobs are not guaranteed to fire on time and cap at 6 hours per job, which doesn't suit holding a persistent live-chat connection. Treat historical batch scraping as the GitHub Actions job; treat live-chat capture as a separate, smaller always-on worker (or a polling-based fallback) — don't force it into the same cron model.

---

## O. Docker Architecture

Only the FastAPI inference service needs containerizing — the dashboard (Streamlit Cloud/Vercel) and scrapers (GitHub Actions runners) don't.

```text
deployment/docker/
├── Dockerfile.api      # installs deps, copies src/ + api/, loads models at startup
└── .dockerignore        # excludes data/, notebooks/, results/, .git
```

Key concerns: pin dependency versions exactly (HF Spaces builds should be reproducible), load all four model checkpoints once at container start (not per-request), and set `HF_HOME`/cache env vars so checkpoints pulled from the Hub are cached in the image layer rather than re-downloaded on every cold start.

---

## P. Configuration & Secrets

```text
configs/*.yaml     # non-secret: model names, hyperparameters, label map paths
.env.example        # documents required env vars, committed
.env                 # actual secrets, gitignored
```

Local dev: `.env` loaded via `python-dotenv`. Production (GitHub Actions, HF Spaces): secrets injected via **GitHub Secrets** and **HF Spaces secrets settings**, never written to any file in the repo. Rule: if a value would break something by being public (DB connection string, API keys), it lives in `.env`/platform secrets, never in `configs/*.yaml`.

---

## Q. Dependency Management

**Recommendation: `pyproject.toml`** (with `pip`/`uv` for installs), not `requirements.txt` or Conda.

- `requirements.txt` lacks structured metadata and dev/prod dependency separation.
- Conda is heavier and less consistent between Windows local dev, Docker, and HF Spaces (which expects pip-installable environments).
- `pyproject.toml` works cleanly across local Windows + Jupyter, Docker, GitHub Actions, and HF Spaces, and lets you separate `[project.dependencies]` from `[project.optional-dependencies.dev]` (pytest, notebook tooling) cleanly.

---

## R. Free-Tier Cloud Architecture

```text
Developer → GitHub → GitHub Actions → Postgres (Supabase/Neon) → FastAPI (HF Spaces) → Dashboard (Streamlit/Vercel)
```

| Service | Role | Free-tier limits to know | Sleep/idle behavior | Alternative |
|---|---|---|---|---|
| GitHub Actions | Scheduled scraping, tests, deploy | 2,000 min/month (public repos: unlimited) | Scheduled jobs deprioritized under load, not guaranteed on-time | Self-hosted runner (not needed yet) |
| Supabase / Neon | Postgres storage | ~500MB–1GB storage; connection limits | Neon suspends compute after inactivity (cold start); Supabase pauses project after ~1 week idle | Railway free tier |
| Hugging Face Spaces (CPU Basic) | FastAPI + model inference | Limited RAM/CPU, no GPU | Sleeps after inactivity; cold start can take 30–60s+ to reload models | Render free tier (also sleeps) |
| Streamlit Community Cloud / Vercel | Dashboard | Streamlit: resource caps, sleeps after inactivity; Vercel: fine for static/light frontends, less suited to Python apps | Streamlit apps sleep; Vercel functions have execution time limits | Either is fine — Streamlit if dashboard stays Python-native |

This is **designed to operate within free-tier limits at the expected project scale** (40k comments, single-region, moderate traffic) — not promised as free forever or infinitely scalable.

---

## S. What to Commit vs Ignore

| Commit | Gitignore |
|---|---|
| `src/`, `api/`, `dashboard/`, `scripts/`, `tests/`, `configs/*.yaml` | `data/raw/`, `data/interim/`, `data/processed/` (actual files) |
| `models/*/config.json`, `label_map.json` | `models/*/checkpoints/` |
| Small `results/` plots and metric JSON/CSV | Large prediction dumps, verbose experiment logs |
| `.env.example` | `.env` |
| `docs/`, `README.md` | Jupyter notebook outputs (strip before commit) |

---

## T. Migration Plan (Safe, Incremental)

1. **Backup everything** — zip the current messy project as-is before touching anything.
2. **Create the repo skeleton** — empty folders per Section A, add `.gitignore`/`pyproject.toml`.
3. **Move raw data untouched** into `data/raw/`, organized by source/date — don't clean yet.
4. **Sort existing notebooks** into the numbered `notebooks/` folders by what they actually do (a "cleaning + EDA" notebook gets split into two).
5. **Extract reusable code** from notebooks into `src/public_pulse/` module by module, starting with data loading/cleaning (most reused).
6. **Finish building `src/`** — training, evaluation, inference modules, backed by the extracted functions.
7. **Reorganize existing trained models** (if any) into `models/layerN/`, push checkpoints to HF Hub.
8. **Add the test suite** — starting with data cleaning and label validation (highest breakage risk).
9. **Stand up the database layer** — schema, SQLAlchemy models, migrate any Excel/Sheets data into Postgres.
10. **Build the FastAPI service** — reading from `src/public_pulse/inference`.
11. **Build the dashboard** — reading from Postgres/API only.
12. **Add GitHub Actions** — tests first, then scraper cron, then deploy.
13. **Dockerize the API.**
14. **Deploy** — Postgres → HF Spaces → dashboard, in that order.

---

## U. Recommended Implementation Roadmap

1. Repo skeleton + `pyproject.toml` + `.gitignore` (Section T, steps 1–2)
2. Database schema stood up in Supabase/Neon, existing Excel/Sheets data migrated in
3. `src/public_pulse/data` + `preprocessing` extracted and tested — this unblocks everything downstream
4. Golden Sample annotation completed using the finalized taxonomy
5. Layer 1 (utility) trained first — cheapest, highest leverage (filters junk before Layers 2–4 ever run)
6. Layers 2–4 trained in sequence, each with its own notebook family and `src/models/layerN.py`
7. Cascade inference (`src/public_pulse/inference/cascade.py`) built and tested end-to-end on held-out data
8. FastAPI service wrapping the cascade, deployed to HF Spaces as a **scheduled batch scorer**, not live inference
9. Dashboard built against pre-scored Postgres data
10. GitHub Actions wired for scraper cron + tests + deploy
11. Docker + final deployment polish

---

### Recommended Final Architecture (single answer, Section 20)

Everything above **is** the one recommended architecture — no competing alternatives. The core commitments driving every decision: raw data is sacred and untouched (`data/raw/`), all reusable logic lives in one importable package (`src/public_pulse/`), each of the four layers is an independently trained/versioned model sharing only infrastructure, inference runs as a scheduled batch job rather than live per-request, and every free-tier service is chosen because it fits this specific batch-oriented shape without requiring a paid always-on server anywhere in the stack.
