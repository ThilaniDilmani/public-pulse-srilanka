# Public Pulse — Database Schema (conceptual)

programs (id, name, platform, channel_url)
videos (id, program_id FK, youtube_video_id, title, published_at, is_live)
comments (id, video_id FK, author_hash, text_raw, posted_at, scraped_at)
annotations (id, comment_id FK, annotator, layer, label, created_at)
layer_predictions (id, comment_id FK, layer, label, confidence, model_version_id FK, predicted_at)
model_versions (id, layer, checkpoint_ref, trained_at, metrics_json)
processing_runs (id, run_type, started_at, finished_at, status, rows_processed)
