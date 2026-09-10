#!/usr/bin/env python3
"""Batch-score unscored comments through the layer1 -> layer2 -> layer4
cascade and write results to layer_predictions. Intended to run on a
schedule, not per-request. (There is no third stage in this cascade --
see docs/taxonomy.md for why.)

Not implemented yet -- this is ETL/database-integration work (Phase 7),
downstream of the model integration built in Phase 4
(src/public_pulse/inference/cascade.py). Even once implemented, running
this for real remains blocked until a real checkpoint is accessible (see
docs/MODEL_REGISTRY.md) -- InferenceCascade.from_config() will raise
CheckpointNotFoundError until then.
"""


"""
Public Pulse — production batch inference runner.

Scores pending YouTube comments through the active cascade:

    Layer 1 (text_raw)
        ├── NOISE  -> stop; store Layer 1 only; status=noise_exit
        └── VALID  -> Layer 2 (text_clean) + Layer 4 (text_clean)
                         -> store all three predictions; status=scored

This script is intentionally separate from the FastAPI request path.
It is safe to re-run: comments already in a terminal processing state
(scored/noise_exit) are skipped by default.

The script uses the existing:
    - InferenceCascade
    - production preprocessing/cascade contract
    - SQLAlchemy database session
    - PostgreSQL schema created by Alembic

It does NOT:
    - retrain models
    - call Gemini
    - perform evidence retrieval
    - perform faithfulness verification
    - create Layer 3
    - expose author_hash or text_raw through the API

Usage:
    python scripts/run_inference.py
    python scripts/run_inference.py --batch-size 16
    python scripts/run_inference.py --limit 100
    python scripts/run_inference.py --retry-errors
    python scripts/run_inference.py --dry-run
    python scripts/run_inference.py --reset-errors

Environment:
    DATABASE_URL
    PUBLIC_PULSE_LAYER1_CHECKPOINT_PATH   (optional; normally config-driven)
    PUBLIC_PULSE_LAYER2_CHECKPOINT_PATH   (optional)
    PUBLIC_PULSE_LAYER4_CHECKPOINT_PATH   (optional)
"""

import argparse
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, and_, func, select, update
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError

# ---------------------------------------------------------------------------
# Project-root / environment setup
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from public_pulse.database.session import SessionLocal  # noqa: E402
from public_pulse.inference.cascade import InferenceCascade  # noqa: E402


LOG = logging.getLogger("public_pulse.run_inference")

VALID_LAYERS = {"layer1", "layer2", "layer4"}
LAYER_ORDER = ("layer1", "layer2", "layer4")

# These are the labels actually used by the current Public Pulse taxonomy.
LAYER1_LABELS = {"VALID", "NOISE"}
LAYER2_LABELS = {
    "TOPIC_ECON_SERV",
    "TOPIC_GOV",
    "TOPIC_LAW",
    "TOPIC_FOR",
    "TOPIC_MEDIA",
}
LAYER4_LABELS = {
    "STANCE_CRIT",
    "STANCE_NEUT",
    "STANCE_SUPP",
}

# The known deployed checkpoints. These are defaults only; the existing
# model/config factory remains the source of model loading behavior.
DEFAULT_CHECKPOINTS = {
    "layer1": REPO_ROOT / "models" / "layer1_utility" / "checkpoints" / "best_model",
    "layer2": REPO_ROOT / "models" / "layer2_topic" / "checkpoints" / "best_model",
    "layer4": REPO_ROOT / "models" / "layer4_stance" / "checkpoints" / "best_model",
}

# Metrics verified during model/checkpoint validation.
DEFAULT_MODEL_INFO = {
    "layer1": {
        "base_model": "xlm-roberta-base",
        "best_metric_name": "macro_f1",
        "best_metric_value": 0.9912,
    },
    "layer2": {
        "base_model": "xlm-roberta-base",
        "best_metric_name": "macro_f1",
        "best_metric_value": 0.7050,
    },
    "layer4": {
        "base_model": "xlm-roberta-base",
        "best_metric_name": "macro_f1",
        "best_metric_value": 0.8649,
    },
}


@dataclass
class RunStats:
    discovered: int = 0
    processed: int = 0
    scored: int = 0
    noise: int = 0
    errors: int = 0
    predictions_inserted: int = 0
    skipped: int = 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score pending Public Pulse comments with Layer 1 -> Layer 2 -> Layer 4."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Number of comments sent to the cascade per batch (default: 16).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of comments to process in this run.",
    )
    parser.add_argument(
        "--retry-errors",
        action="store_true",
        help="Also process comments currently marked as error.",
    )
    parser.add_argument(
        "--reset-errors",
        action="store_true",
        help="Convert existing error comments back to pending before processing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run model inference without writing predictions/statuses to PostgreSQL.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging level.",
    )
    return parser.parse_args(argv)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def require_dependencies() -> None:
    """Fail early with a useful message if the ML stack is incomplete."""
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "PyTorch/Transformers are required for production inference. "
            "Activate the project venv and install the project's ML dependencies."
        ) from exc


def load_database_tables() -> dict[str, Table]:
    """
    Reflect the already-migrated PostgreSQL tables.

    Reflection keeps this runner aligned with the live Alembic schema and
    avoids duplicating ORM definitions inside a one-off ETL script.
    """
    metadata = MetaData()
    return {
        name: Table(name, metadata, autoload_with=SessionLocal.kw["bind"])
        for name in (
            "comments",
            "layer_predictions",
            "model_versions",
            "pipeline_runs",
        )
    }


def database_health_check(db) -> None:
    db.execute(select(func.count()).select_from(load_database_tables()["comments"]))
    LOG.info("Database connection: OK")


def checkpoint_path(layer: str) -> Path:
    env_name = f"PUBLIC_PULSE_{layer.upper()}_CHECKPOINT_PATH"
    configured = os.getenv(env_name, "").strip()
    path = Path(configured) if configured else DEFAULT_CHECKPOINTS[layer]
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def verify_checkpoints() -> None:
    missing = []
    for layer in LAYER_ORDER:
        path = checkpoint_path(layer)
        if not path.exists():
            missing.append(f"{layer}: {path}")
    if missing:
        raise FileNotFoundError(
            "One or more production checkpoints are missing:\n  "
            + "\n  ".join(missing)
        )
    LOG.info("All three production checkpoints are present.")


def _enum_value(value: Any) -> str:
    """Normalize SQLAlchemy enum values and plain strings."""
    if value is None:
        return ""
    raw = getattr(value, "value", value)
    return str(raw)


def _prediction_field(prediction: Any, field: str, default: Any = None) -> Any:
    if prediction is None:
        return default
    if isinstance(prediction, dict):
        return prediction.get(field, default)
    return getattr(prediction, field, default)


def normalize_prediction(prediction: Any, expected_layer: str) -> dict[str, Any]:
    """
    Convert either the project's LayerPrediction dataclass or a dict into
    the database contract.
    """
    layer = _enum_value(_prediction_field(prediction, "layer"))
    label = _enum_value(_prediction_field(prediction, "label"))
    label_id = _prediction_field(prediction, "label_id")
    confidence = _prediction_field(prediction, "confidence")

    if layer != expected_layer:
        raise ValueError(
            f"Cascade returned layer={layer!r}; expected {expected_layer!r}."
        )
    if not label:
        raise ValueError(f"{expected_layer}: empty prediction label.")
    if label_id is None:
        raise ValueError(f"{expected_layer}: missing label_id.")
    if confidence is None:
        raise ValueError(f"{expected_layer}: missing confidence.")

    confidence = float(confidence)
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(
            f"{expected_layer}: confidence {confidence} is outside [0, 1]."
        )

    allowed = {
        "layer1": LAYER1_LABELS,
        "layer2": LAYER2_LABELS,
        "layer4": LAYER4_LABELS,
    }[expected_layer]

    if label not in allowed:
        raise ValueError(
            f"{expected_layer}: invalid label {label!r}; allowed={sorted(allowed)}"
        )

    return {
        "layer": expected_layer,
        "label": label,
        "label_id": int(label_id),
        "confidence": confidence,
    }


def extract_cascade_results(
    cascade: Any,
    raw_texts: list[str],
) -> list[Any]:
    """
    Prefer the cascade's batch API when available.

    The fallback calls the already-implemented single-item cascade. This makes
    the runner compatible with both versions of the Phase 4 cascade contract.
    """
    batch_method = getattr(cascade, "predict_batch", None)
    if callable(batch_method):
        results = batch_method(raw_texts)
        if len(results) != len(raw_texts):
            raise RuntimeError(
                f"Cascade returned {len(results)} results for {len(raw_texts)} comments."
            )
        return list(results)

    single_method = getattr(cascade, "predict", None)
    if not callable(single_method):
        raise RuntimeError(
            "InferenceCascade exposes neither predict_batch() nor predict()."
        )

    return [single_method(text) for text in raw_texts]


def result_layers(result: Any) -> tuple[Any, Any, Any]:
    """
    Extract layer1/layer2/layer4 from the project's CascadeResult.

    Supports both dataclass attributes and dictionary-shaped results.
    """
    if isinstance(result, dict):
        return (
            result.get("layer1") or result.get("utility"),
            result.get("layer2") or result.get("topic"),
            result.get("layer4") or result.get("stance"),
        )

    return (
        getattr(result, "layer1", None),
        getattr(result, "layer2", None),
        getattr(result, "layer4", None),
    )


def get_or_create_model_versions(db, tables: dict[str, Table]) -> dict[str, Any]:
    """
    Resolve one active model_versions row for each active layer.

    If a layer has no active row yet, register the verified local checkpoint
    as the active version. Existing active versions are never replaced by
    this runner.
    """
    model_versions = tables["model_versions"]
    resolved: dict[str, Any] = {}

    for layer in LAYER_ORDER:
        row = db.execute(
            select(model_versions)
            .where(
                and_(
                    model_versions.c.layer == layer,
                    model_versions.c.is_active.is_(True),
                )
            )
            .limit(1)
        ).mappings().first()

        if row:
            resolved[layer] = row["id"]
            LOG.info(
                "Active model version: %s -> %s",
                layer,
                row["id"],
            )
            continue

        # Reuse an existing version for the exact checkpoint if one exists.
        checkpoint = str(checkpoint_path(layer))
        existing = db.execute(
            select(model_versions)
            .where(
                and_(
                    model_versions.c.layer == layer,
                    model_versions.c.checkpoint_ref == checkpoint,
                )
            )
            .limit(1)
        ).mappings().first()

        if existing:
            db.execute(
                update(model_versions)
                .where(model_versions.c.layer == layer)
                .values(is_active=False)
            )
            db.execute(
                update(model_versions)
                .where(model_versions.c.id == existing["id"])
                .values(is_active=True)
            )
            resolved[layer] = existing["id"]
            LOG.info(
                "Activated existing model version: %s -> %s",
                layer,
                existing["id"],
            )
            continue

        info = DEFAULT_MODEL_INFO[layer]
        model_id = uuid.uuid4()

        # Deactivate any stale rows first. The migration also enforces a
        # partial unique index for one active version per layer.
        db.execute(
            update(model_versions)
            .where(model_versions.c.layer == layer)
            .values(is_active=False)
        )

        db.execute(
            model_versions.insert().values(
                id=model_id,
                layer=layer,
                checkpoint_ref=checkpoint,
                base_model=info["base_model"],
                best_metric_name=info["best_metric_name"],
                best_metric_value=info["best_metric_value"],
                metrics_json={
                    "macro_f1": info["best_metric_value"],
                    "source": "verified Public Pulse model registry",
                },
                is_active=True,
            )
        )

        resolved[layer] = model_id
        LOG.info(
            "Registered active model version: %s -> %s (%s)",
            layer,
            model_id,
            checkpoint,
        )

    return resolved


def reset_error_comments(db, comments: Table) -> int:
    result = db.execute(
        update(comments)
        .where(comments.c.processing_status == "error")
        .values(processing_status="pending")
    )
    db.commit()
    return int(result.rowcount or 0)


def load_pending_comments(
    db,
    comments: Table,
    limit: int | None,
    retry_errors: bool,
) -> list[Any]:
    statuses = ["pending"]
    if retry_errors:
        statuses.append("error")

    stmt = (
        select(comments)
        .where(comments.c.processing_status.in_(statuses))
        .order_by(comments.c.created_at.asc(), comments.c.id.asc())
    )

    if limit is not None:
        stmt = stmt.limit(limit)

    return list(db.execute(stmt).mappings().all())


def insert_prediction(
    db,
    layer_predictions: Table,
    *,
    comment_id: Any,
    model_version_id: Any,
    prediction: dict[str, Any],
    predicted_at: datetime,
) -> None:
    """
    Insert one prediction.

    The schema's unique constraint prevents duplicate rows for the same
    comment/layer/model-version. Because comments are processed only when
    pending/error, this should normally be a plain insert.
    """
    db.execute(
        layer_predictions.insert().values(
            id=uuid.uuid4(),
            comment_id=comment_id,
            model_version_id=model_version_id,
            layer=prediction["layer"],
            label=prediction["label"],
            label_id=prediction["label_id"],
            confidence=prediction["confidence"],
            predicted_at=predicted_at,
        )
    )


def process_batch(
    db,
    tables: dict[str, Table],
    cascade: Any,
    model_versions: dict[str, Any],
    rows: list[Any],
    *,
    dry_run: bool,
    stats: RunStats,
) -> None:
    comments = tables["comments"]
    layer_predictions = tables["layer_predictions"]

    raw_texts = [
        "" if row["text_raw"] is None else str(row["text_raw"])
        for row in rows
    ]

    results = extract_cascade_results(cascade, raw_texts)

    for row, result in zip(rows, results):
        comment_id = row["id"]
        predicted_at = datetime.now(timezone.utc)

        try:
            layer1_raw, layer2_raw, layer4_raw = result_layers(result)

            p1 = normalize_prediction(layer1_raw, "layer1")

            if p1["label"] == "NOISE":
                if not dry_run:
                    insert_prediction(
                        db,
                        layer_predictions,
                        comment_id=comment_id,
                        model_version_id=model_versions["layer1"],
                        prediction=p1,
                        predicted_at=predicted_at,
                    )
                    db.execute(
                        update(comments)
                        .where(comments.c.id == comment_id)
                        .values(processing_status="noise_exit")
                    )

                stats.noise += 1
                stats.processed += 1
                stats.predictions_inserted += 1
                continue

            # VALID comments must have both downstream predictions.
            if layer2_raw is None or layer4_raw is None:
                raise ValueError(
                    "Layer 1 predicted VALID but Layer 2 or Layer 4 result is missing."
                )

            p2 = normalize_prediction(layer2_raw, "layer2")
            p4 = normalize_prediction(layer4_raw, "layer4")

            if not dry_run:
                insert_prediction(
                    db,
                    layer_predictions,
                    comment_id=comment_id,
                    model_version_id=model_versions["layer1"],
                    prediction=p1,
                    predicted_at=predicted_at,
                )
                insert_prediction(
                    db,
                    layer_predictions,
                    comment_id=comment_id,
                    model_version_id=model_versions["layer2"],
                    prediction=p2,
                    predicted_at=predicted_at,
                )
                insert_prediction(
                    db,
                    layer_predictions,
                    comment_id=comment_id,
                    model_version_id=model_versions["layer4"],
                    prediction=p4,
                    predicted_at=predicted_at,
                )
                db.execute(
                    update(comments)
                    .where(comments.c.id == comment_id)
                    .values(processing_status="scored")
                )

            stats.scored += 1
            stats.processed += 1
            stats.predictions_inserted += 3

        except Exception as exc:
            LOG.exception(
                "Inference failed for comment %s: %s",
                comment_id,
                exc,
            )

            # Isolate the bad record. Other comments in the batch can still
            # be committed.
            db.rollback()

            if not dry_run:
                db.execute(
                    update(comments)
                    .where(comments.c.id == comment_id)
                    .values(processing_status="error")
                )
                db.commit()

            stats.errors += 1


def create_pipeline_run(db, tables: dict[str, Table], *, dry_run: bool) -> Any:
    if dry_run:
        return None

    pipeline_runs = tables["pipeline_runs"]
    run_id = uuid.uuid4()

    db.execute(
        pipeline_runs.insert().values(
            id=run_id,
            run_type="batch_inference",
            started_at=datetime.now(timezone.utc),
            status="running",
            comments_processed=0,
            comments_scored=0,
            comments_noise=0,
            triggered_by="manual",
        )
    )
    db.commit()

    return run_id


def finish_pipeline_run(
    db,
    tables: dict[str, Table],
    run_id: Any,
    stats: RunStats,
    *,
    status: str,
    error_message: str | None = None,
) -> None:
    if run_id is None:
        return

    pipeline_runs = tables["pipeline_runs"]

    db.execute(
        update(pipeline_runs)
        .where(pipeline_runs.c.id == run_id)
        .values(
            finished_at=datetime.now(timezone.utc),
            status=status,
            comments_processed=stats.processed,
            comments_scored=stats.scored,
            comments_noise=stats.noise,
            error_message=error_message,
        )
    )
    db.commit()


def print_summary(stats: RunStats, *, dry_run: bool) -> None:
    print()
    print("=" * 72)
    print("PUBLIC PULSE — INFERENCE SUMMARY")
    print("=" * 72)
    print(f"Comments discovered : {stats.discovered:,}")
    print(f"Comments processed  : {stats.processed:,}")
    print(f"VALID / scored      : {stats.scored:,}")
    print(f"NOISE / early exit  : {stats.noise:,}")
    print(f"Errors              : {stats.errors:,}")
    print(f"Predictions created : {stats.predictions_inserted:,}")
    print(f"Mode                : {'DRY RUN' if dry_run else 'DATABASE WRITE'}")
    print("=" * 72)

    if stats.errors:
        print(
            "WARNING: Some comments were marked error. "
            "Re-run with --retry-errors after investigating the first failure."
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level)

    if args.batch_size <= 0:
        LOG.error("--batch-size must be greater than zero.")
        return 2

    if args.limit is not None and args.limit <= 0:
        LOG.error("--limit must be greater than zero.")
        return 2

    if args.reset_errors and args.dry_run:
        LOG.error("--reset-errors cannot be combined with --dry-run.")
        return 2

    db = None
    run_id = None
    stats = RunStats()

    try:
        require_dependencies()
        verify_checkpoints()

        db = SessionLocal()
        tables = load_database_tables()
        database_health_check(db)

        if args.reset_errors:
            reset_count = reset_error_comments(db, tables["comments"])
            LOG.info("Reset %d error comments to pending.", reset_count)

        rows = load_pending_comments(
            db,
            tables["comments"],
            args.limit,
            args.retry_errors,
        )
        stats.discovered = len(rows)

        if not rows:
            LOG.info("No pending comments require inference.")
            print_summary(stats, dry_run=args.dry_run)
            return 0

        LOG.info("Comments queued for inference: %d", len(rows))

        # Build the production cascade once. The model wrappers are designed
        # to load once and then be reused for all batches.
        LOG.info("Loading Layer 1 -> Layer 2 -> Layer 4 inference cascade...")
        cascade = InferenceCascade.from_config()
        LOG.info("Inference cascade ready.")

        model_versions = get_or_create_model_versions(
            db,
            tables,
        )

        if not args.dry_run:
            db.commit()
            run_id = create_pipeline_run(
                db,
                tables,
                dry_run=False,
            )

        for start in range(0, len(rows), args.batch_size):
            batch = rows[start : start + args.batch_size]
            LOG.info(
                "Processing comments %d-%d of %d...",
                start + 1,
                start + len(batch),
                len(rows),
            )

            process_batch(
                db,
                tables,
                cascade,
                model_versions,
                batch,
                dry_run=args.dry_run,
                stats=stats,
            )

            if not args.dry_run:
                # Batch-level commits make the run resumable. If the process
                # stops after batch N, earlier completed comments stay scored.
                db.commit()

            LOG.info(
                "Progress: processed=%d/%d, scored=%d, noise=%d, errors=%d",
                stats.processed,
                stats.discovered,
                stats.scored,
                stats.noise,
                stats.errors,
            )

        if not args.dry_run:
            finish_pipeline_run(
                db,
                tables,
                run_id,
                stats,
                status="success" if stats.errors == 0 else "error",
                error_message=(
                    f"{stats.errors} comment(s) failed during inference."
                    if stats.errors
                    else None
                ),
            )

        print_summary(stats, dry_run=args.dry_run)

        # A non-zero exit code is useful to CI/schedulers if individual
        # comments failed, while successful comments remain persisted.
        return 1 if stats.errors else 0

    except KeyboardInterrupt:
        LOG.warning("Inference interrupted by user.")
        if db is not None and run_id is not None:
            try:
                tables = load_database_tables()
                finish_pipeline_run(
                    db,
                    tables,
                    run_id,
                    stats,
                    status="error",
                    error_message="Interrupted by user.",
                )
            except Exception:
                LOG.exception("Could not update interrupted pipeline run.")
        return 130

    except (OperationalError, DBAPIError, SQLAlchemyError) as exc:
        LOG.exception("Database error during inference: %s", exc)
        if db is not None and run_id is not None:
            try:
                tables = load_database_tables()
                finish_pipeline_run(
                    db,
                    tables,
                    run_id,
                    stats,
                    status="error",
                    error_message=str(exc),
                )
            except Exception:
                LOG.exception("Could not update failed pipeline run.")
        return 1

    except Exception as exc:
        LOG.exception("Inference failed: %s", exc)
        if db is not None and run_id is not None:
            try:
                tables = load_database_tables()
                finish_pipeline_run(
                    db,
                    tables,
                    run_id,
                    stats,
                    status="error",
                    error_message=str(exc),
                )
            except Exception:
                LOG.exception("Could not update failed pipeline run.")
        return 1

    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    raise SystemExit(main())
