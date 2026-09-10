# Public Pulse — Database Schema

**Status: IMPLEMENTED (Phase 5B)**
**Active architecture: Layer 1 → Layer 2 + Layer 4. Layer 3 has been permanently removed.**

The `layer` discriminator column appears in `model_versions`, `layer_predictions`,
`annotations`, and `evidence`. It accepts **exactly three values**:
`layer1`, `layer2`, `layer4`. There is no `layer3` — this is a documented,
intentional research-scope decision, not a gap to fill later (see `docs/taxonomy.md`).

---

## Technology

| Component | Choice |
|---|---|
| Database | PostgreSQL (Supabase / Neon free tier) |
| ORM | SQLAlchemy 2.x (`DeclarativeBase`) |
| Migrations | Alembic |
| Driver | psycopg2-binary |
| Config | `DATABASE_URL` env var (never hard-coded) |

---

## Entity Hierarchy

```
channels
  └── programs          (many programs → one channel; several programs share a channel)
        └── videos      (many videos → one program)
              └── comments
                    ├── layer_predictions  (1 per NOISE comment; 3 per VALID comment)
                    ├── annotations        (manual training labels)
                    └── evidence           (future grounded-LLM persistence target)

model_versions  ──────────────────→ layer_predictions (FK)
pipeline_runs   (standalone audit log)
insights        (future insight store; nullable FK → programs)
```

---

## Text Input Contract

Both fields are stored per comment. **Never merge them.**

| Column | Layer input | Description |
|---|---|---|
| `comments.text_raw` | Layer 1 | Original scraped YouTube text — no preprocessing |
| `comments.text_clean` | Layer 2 and Layer 4 | Output of `clean_text()` preprocessing |

---

## Table Definitions

### `channels`

Distinct from programs. Multiple programs may air on the same channel.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `youtube_channel_id` | VARCHAR(64) | NOT NULL, UNIQUE |
| `name` | VARCHAR(255) | NOT NULL |
| `channel_url` | TEXT | nullable |
| `description` | TEXT | nullable |
| `subscriber_count` | BIGINT | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

---

### `programs`

14 target programs, each belonging to a channel.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `channel_id` | UUID | NOT NULL, FK → channels.id RESTRICT |
| `name` | VARCHAR(255) | NOT NULL |
| `platform` | VARCHAR(32) | NOT NULL, DEFAULT 'youtube' |
| `program_type` | VARCHAR(64) | **nullable** — not yet authoritatively defined; do not invent values |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Index:** `ix_programs_channel_id(channel_id)`

---

### `videos`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `program_id` | UUID | NOT NULL, FK → programs.id RESTRICT |
| `youtube_video_id` | VARCHAR(64) | NOT NULL, UNIQUE |
| `title` | TEXT | nullable |
| `description` | TEXT | nullable |
| `published_at` | TIMESTAMPTZ | nullable |
| `duration_seconds` | INTEGER | nullable |
| `is_live` | BOOLEAN | NOT NULL, DEFAULT false |
| `comment_count` | INTEGER | nullable |
| `scraped_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes:** `ix_videos_program_published(program_id, published_at)`, `ix_videos_published_at(published_at)`

---

### `comments`

Primary idempotency key: `youtube_comment_id`. The scraper uses this to avoid
re-inserting the same comment on repeated runs.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `video_id` | UUID | NOT NULL, FK → videos.id RESTRICT |
| `youtube_comment_id` | VARCHAR(128) | NOT NULL, UNIQUE |
| `author_hash` | VARCHAR(64) | nullable (SHA-256 of author channel ID) |
| `text_raw` | TEXT | NOT NULL — Layer 1 input |
| `text_clean` | TEXT | NOT NULL — Layer 2 / Layer 4 input |
| `like_count` | INTEGER | NOT NULL, DEFAULT 0 |
| `reply_count` | INTEGER | NOT NULL, DEFAULT 0 |
| `posted_at` | TIMESTAMPTZ | nullable |
| `scraped_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| `is_reply` | BOOLEAN | NOT NULL, DEFAULT false |
| `parent_comment_id` | UUID | nullable, FK → comments.id SET NULL (reply threading, not yet implemented) |
| `processing_status` | ENUM | NOT NULL, DEFAULT 'pending' |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**`processing_status` values:** `pending` · `scored` · `error` · `noise_exit`

**Indexes:** `ix_comments_video_id`, `ix_comments_processing_status`, `ix_comments_posted_at`

---

### `model_versions`

Tracks trained checkpoint provenance per layer.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `layer` | ENUM | NOT NULL — `layer1` / `layer2` / `layer4` only |
| `checkpoint_ref` | TEXT | NOT NULL |
| `base_model` | VARCHAR(128) | nullable |
| `trained_at` | TIMESTAMPTZ | nullable |
| `best_metric_name` | VARCHAR(64) | nullable |
| `best_metric_value` | FLOAT | nullable |
| `metrics_json` | JSONB | nullable |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT false |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Partial unique index:** `UNIQUE(layer) WHERE is_active = TRUE`
— enforces at most one active version per layer in PostgreSQL.

---

### `layer_predictions`

One row per (comment, layer, model_version) triple.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `comment_id` | UUID | NOT NULL, FK → comments.id CASCADE |
| `model_version_id` | UUID | NOT NULL, FK → model_versions.id RESTRICT |
| `layer` | ENUM | NOT NULL — `layer1` / `layer2` / `layer4` only |
| `label` | VARCHAR(64) | NOT NULL |
| `label_id` | SMALLINT | NOT NULL |
| `confidence` | FLOAT | NOT NULL |
| `predicted_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Unique:** `UNIQUE(comment_id, layer, model_version_id)` — prevents duplicate scoring

**Expected rows per comment:**
- NOISE comment: **1 row** (layer1 only — do not insert placeholder L2/L4 rows)
- VALID comment: **3 rows** (layer1 + layer2 + layer4)

**Indexes:** `ix_layer_predictions_comment_layer`, `ix_layer_predictions_layer_label_time`

---

### `pipeline_runs`

Audit log for batch scoring and scraping pipeline executions.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `run_type` | VARCHAR(64) | NOT NULL |
| `started_at` | TIMESTAMPTZ | NOT NULL |
| `finished_at` | TIMESTAMPTZ | nullable |
| `status` | ENUM | NOT NULL — `running` / `success` / `error` |
| `comments_processed` | INTEGER | nullable |
| `comments_scored` | INTEGER | nullable |
| `comments_noise` | INTEGER | nullable |
| `error_message` | TEXT | nullable |
| `triggered_by` | VARCHAR(128) | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Index:** `ix_pipeline_runs_started_at`

---

### `annotations`

Manual human labels used for training data provenance.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `comment_id` | UUID | NOT NULL, FK → comments.id CASCADE |
| `annotator` | VARCHAR(128) | NOT NULL |
| `layer` | ENUM | NOT NULL — `layer1` / `layer2` / `layer4` only |
| `label` | VARCHAR(64) | NOT NULL |
| `confidence_score` | FLOAT | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Unique:** `UNIQUE(comment_id, annotator, layer)` — one label per annotator per layer per comment

---

### `evidence`

Persistence target for the future grounded-LLM system. **Not populated in Phase 5.**

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `comment_id` | UUID | NOT NULL, FK → comments.id CASCADE |
| `evidence_type` | VARCHAR(64) | NOT NULL |
| `layer` | ENUM | nullable — `layer1` / `layer2` / `layer4` only |
| `label` | VARCHAR(64) | nullable |
| `confidence` | FLOAT | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

---

### `insights`

Persistence target for future aggregated insights. **Not populated in Phase 5.**

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `program_id` | UUID | nullable, FK → programs.id SET NULL (NULL = system-wide insight) |
| `insight_type` | VARCHAR(64) | NOT NULL |
| `period_start` | DATE | nullable |
| `period_end` | DATE | nullable |
| `payload_json` | JSONB | NOT NULL |
| `generated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

---

## Idempotency Rules

| Table | Idempotency Key | Behaviour |
|---|---|---|
| `channels` | `youtube_channel_id` | `upsert_channel()` — update name/url on re-scrape |
| `videos` | `youtube_video_id` | `upsert_video()` — update title/counts on re-scrape |
| `comments` | `youtube_comment_id` | `upsert_comment()` — update text/counts on re-scrape |
| `layer_predictions` | `(comment_id, layer, model_version_id)` | skip if exists; no re-scoring with same model |
| `annotations` | `(comment_id, annotator, layer)` | DB UNIQUE constraint |

---

## Layer Taxonomy (enforced by SAEnum / PostgreSQL ENUM)

```
Layer 1:  VALID | NOISE
Layer 2:  TOPIC_ECON_SERV | TOPIC_GOV | TOPIC_LAW | TOPIC_FOR | TOPIC_MEDIA
Layer 4:  STANCE_CRIT | STANCE_NEUT | STANCE_SUPP
```

Layer 3 does not exist. The value `'layer3'` is rejected by the PostgreSQL
`layer_enum` type and by the SQLAlchemy `LayerEnum` Python enum.

---

## Migration

```bash
# Set DATABASE_URL then run:
alembic upgrade head      # apply all migrations to a live PostgreSQL DB
alembic downgrade base    # revert all migrations (destructive — drops all tables)
alembic history           # view migration chain
```

The Alembic migration (`alembic/versions/0001_initial_schema.py`) creates:
- All 10 tables with full column definitions and FKs
- 3 PostgreSQL enum types (`layer_enum`, `processing_status_enum`, `pipeline_run_status_enum`)
- All indexes listed above
- The partial unique index `UNIQUE(layer) WHERE is_active = TRUE` on `model_versions`
- Native PostgreSQL `JSONB` for `metrics_json` and `payload_json` columns

---

## Implementation Files

| File | Purpose |
|---|---|
| `src/public_pulse/database/models.py` | SQLAlchemy ORM model classes (10 tables) |
| `src/public_pulse/database/session.py` | Engine, SessionLocal, get_db() |
| `src/public_pulse/database/repository.py` | Idempotent repository functions |
| `src/public_pulse/database/__init__.py` | Package exports |
| `alembic/versions/0001_initial_schema.py` | Initial migration |
| `tests/test_database.py` | 23 database tests (SQLite in-memory) |
