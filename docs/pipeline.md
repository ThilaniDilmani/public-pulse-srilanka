# Phase 7 — Production Inference Pipeline Documentation

This document describes the design, architecture, execution workflow, batching, idempotency, model version management, and CLI usage of the production batch inference pipeline in Public Pulse.

---

## 1. Overview & Architecture

The Phase 7 pipeline orchestrates end-to-end batch scoring of YouTube comment data collected during Phase 6. It connects database persistence (Phase 5B), production text preprocessing (Phase 3), model inference cascade (Phase 4), and model version tracking.

### Production Cascade Flow
```
          [Pending Comment in DB] (ProcessingStatus: pending)
                    │
                    ▼
          [Text Cleaner Variant]
         (text_raw preserved, text_clean generated)
                    │
                    ▼
          [Layer 1: Utility Classifier] (Input: text_raw, max_seq_length=256)
           ├── NOISE (1) ──► [Early Exit]
           │                  ├── processing_status = noise_exit
           │                  └── insert Layer 1 prediction
           │
           └── VALID (0) ──► [Continue Cascade]
                              ├── Layer 2: Topic Classifier (Input: text_clean, 5 topics)
                              ├── Layer 4: Stance Classifier (Input: text_clean, 3 stances)
                              ├── processing_status = scored
                              └── insert Layer 1, Layer 2, Layer 4 predictions
```

> [!IMPORTANT]
> **Strict Architectural Rules:**
> - The production cascade consists strictly of **Layer 1 → Layer 2 → Layer 4**.
> - **Layer 3 does NOT exist** in this pipeline and must never be reintroduced.
> - **Models are loaded ONCE per process** to maximize inference throughput.
> - **`text_raw` is strictly preserved** in the database. `text_clean` is stored on the `Comment` record for inspection and reproducibility.

---

## 2. Component Design

### Module Structure (`public_pulse.pipeline`)
- `config.py`: Defines `PipelineConfig` dataclass (`batch_size`, `max_comments`, `dry_run`, `force_reprocess`).
- `batch_processor.py`: `BatchProcessor` engine that runs the `InferenceCascade` on comment batches, updates `text_clean`, maps `ModelVersion` IDs, applies early-exit for NOISE, updates `processing_status`, and commits batch predictions via the repository.
- `service.py`: `PipelineService` orchestrator and CLI entrypoint. Initializes active `ModelVersion` records (`ensure_model_versions`), runs the batch loop, tracks stats, and logs execution records in `PipelineRun`.
- `__init__.py`: Package exports (`PipelineConfig`, `BatchProcessor`, `PipelineService`, `ensure_model_versions`).

---

## 3. Key Pipeline Features

### A. Model Version Management (`ensure_model_versions`)
Before processing, `ensure_model_versions(db)` ensures that an active `ModelVersion` record exists for `layer1`, `layer2`, and `layer4`. On subsequent runs, existing active `ModelVersion` records are reused without creating duplicates.

### B. Idempotency & Resumability
- **Idempotency**: Predictions are inserted using `insert_predictions()`, which performs `on_conflict_do_nothing` (or checks existing predictions) on `(comment_id, model_version_id, layer)`. Re-running the pipeline on scored comments produces zero duplicate database records.
- **Resumability**: The pipeline queries only comments with `processing_status = 'pending'`. Scored comments (`scored` or `noise_exit`) are automatically skipped on resume.

### C. Transaction Safety & Error Rollback
- Batch processing is committed on a per-batch basis (`db.commit()`).
- If an unhandled exception occurs (e.g. GPU OOM or database connectivity error), the current batch transaction is rolled back (`db.rollback()`), and the failure is logged in `PipelineRun` with `status = 'error'` and the error traceback message.
- Previously committed batches remain safely persisted in the database.

### D. Dry Run Mode
When `--dry-run` is passed:
- Text cleaner and model inference cascade execute normally.
- Predictions and status updates are **NOT** committed to the database.
- No `PipelineRun` audit record is created.

---

## 4. CLI Usage

Run the batch inference pipeline via module invocation:

```bash
python -m public_pulse.pipeline.service [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--batch-size` | `int` | `100` | Number of comments processed in each database transaction batch |
| `--max-comments` | `int` | `None` | Maximum total number of pending comments to process in this run |
| `--dry-run` | `flag` | `False` | Run model inference without persisting predictions or status to DB |
| `--force-reprocess` | `flag` | `False` | Reset all comment statuses to `pending` before starting pipeline |

### Example Commands

#### Standard Production Run (100 comments per batch)
```bash
python -m public_pulse.pipeline.service --batch-size 100
```

#### Test Dry Run (Max 50 comments)
```bash
python -m public_pulse.pipeline.service --batch-size 10 --max-comments 50 --dry-run
```

#### Force Reprocess All Historical Comments
```bash
python -m public_pulse.pipeline.service --force-reprocess --batch-size 200
```

---

## 5. Verification & Testing

The Phase 7 pipeline is fully covered by automated unit and integration tests in `tests/test_pipeline.py`.

### Test Suite Execution
```bash
pytest tests/test_pipeline.py -v
```

### Verified Scenarios (14/14 Passed)
1. `test_empty_input_pipeline`: Gracefully completes with 0 processed comments when database has no pending items.
2. `test_single_comment_valid_cascade`: Single VALID comment runs Layer 1 -> Layer 2 & 4 cascade, status updated to `scored`, 3 predictions saved.
3. `test_single_comment_noise_early_exit`: NOISE comment triggers early exit: status updated to `noise_exit`, 1 prediction saved, Layer 2 & 4 skipped.
4. `test_batch_processing_mixed_valid_and_noise`: Correctly processes mixed batches of VALID and NOISE comments.
5. `test_text_raw_preserved_and_text_clean_generated`: Preserves raw input string in `text_raw` while storing Phase 3 cleaned string in `text_clean`.
6. `test_multilingual_code_mixed_input`: Supports Sinhala, English, Singlish, and code-mixed inputs cleanly.
7. `test_ensure_model_versions_initializes_and_reuses`: Initializes active `ModelVersion` records once and reuses them on subsequent runs without duplication.
8. `test_prediction_idempotency`: Re-running pipeline produces zero duplicate predictions in database.
9. `test_resume_behavior_skips_already_scored`: Automatically skips comments marked `scored` or `noise_exit`.
10. `test_pipelinerun_success_tracking`: Records `PipelineRun` with `status='success'` and accurate counts.
11. `test_partial_failure_rollback_and_pipeline_error_tracking`: Handles batch errors cleanly, logs `status='error'` and exception message in `PipelineRun`.
12. `test_dry_run_mode`: Performs inference without committing database changes.
13. `test_exact_label_mappings`: Verifies taxonomy label mappings match exact project specifications.
14. `test_layer3_absence`: Verifies Layer 3 is strictly absent across pipeline logic, models, and enums.

**Total Project Test Suite Pass Count:** 171 / 171 passed (0 failed).
