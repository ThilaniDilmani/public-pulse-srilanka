# Public Pulse — Model Registry

Phase 2 deliverable: model artifact / checkpoint verification status for
the three active layers (Layer 1 → Layer 2 → Layer 4). This document
records what was actually verified and how, not what is assumed.

**Verification method:** the six authoritative notebooks (as provided
directly, not read from within this repository) were inspected cell by
cell, including their embedded execution outputs. Three of the six
(`02_training.ipynb`, `layer2_02_training_final.ipynb`,
`layer4_02_training_final.ipynb`) contain genuine, internally consistent
Colab execution output — GPU device logs, real package-download progress,
real per-class classification reports, real Sinhala/Singlish tokenization
examples — that constitute strong circumstantial evidence each training
run actually completed. This is evidence from notebook output, not a
verified, loaded model artifact — no checkpoint file was found or loaded
in this environment, and no smoke test was run.

## Summary

| Layer | Status | Reported checkpoint location | Reported best macro-F1 |
|---|---|---|---|
| Layer 1 (Utility) | `ACCESS_UNAVAILABLE` | `/content/drive/MyDrive/public-pulse-srilanka/models/layer1_utility/checkpoints/best_model` (Google Drive) | 0.9912050545456186 |
| Layer 2 (Topic) | `ACCESS_UNAVAILABLE` | `/content/drive/MyDrive/public-pulse-srilanka/models/layer2_topic/checkpoints/best_model` (Google Drive) | 0.7050123837778992 |
| Layer 4 (Stance) | `ACCESS_UNAVAILABLE` | `/content/drive/MyDrive/public-pulse-srilanka/models/layer4_stance/checkpoints/best_model` (Google Drive) | 0.8649461493849765 |

No layer is `AVAILABLE_AND_VERIFIED`. That status requires an actual local
load of the weight files plus a passing inference smoke test — neither was
possible, since this environment has no tool that can reach Google Drive,
and no checkpoint weight file exists anywhere in the repository or in any
file directly uploaded to this conversation.

## Layer 1 — Utility

- **Base model:** `xlm-roberta-base`
- **Labels:** `VALID: 0, NOISE: 1` — reported by the notebook, exactly matches this repo's Phase 1 `label_map.json`
- **Input column:** `text_raw`, `max_seq_length: 256`
- **Artifacts the notebook reports writing:** `checkpoints/best_model/` (HF-format: model weights + tokenizer, via `trainer.save_model()` + `tokenizer.save_pretrained()`), `label_map.json`, `training_metadata.json` (keys: `base_model`, `max_seq_length`, `best_metric`, `best_metric_value`, `random_seed`, `train_rows`, `val_rows`)
- **Reported metrics (from notebook's own printed classification report):** macro-F1 0.99, VALID precision/recall 1.00/1.00 (support 1153), NOISE precision/recall 0.98/0.99 (support 240)
- **Evidence quality:** high — GPU device log ("Tesla T4"), real `TrainOutput` object with loss/runtime/step counts, real per-class support numbers matching the data-prep notebook's reported split sizes (train 6503 / val 1393)
- **What is NOT verified:** the actual weight file's integrity, the model's real output-head shape, or a live inference smoke test — none possible without Drive access

## Layer 2 — Macro Topic

- **Base model:** `xlm-roberta-base`
- **Labels:** `TOPIC_ECON_SERV: 0, TOPIC_FOR: 1, TOPIC_GOV: 2, TOPIC_LAW: 3, TOPIC_MEDIA: 4` — reported by the notebook, exactly matches this repo's Phase 1 `label_map.json`
- **Input column:** `text_clean`, `max_seq_length: 256`
- **Artifacts the notebook reports writing:** same pattern as Layer 1, plus `class_weights.json` was *read* (pre-existing, produced during data preparation) and echoed into `training_metadata.json` under `class_weights_used`
- **Reported metrics:** macro-F1 0.71; per-class F1 — TOPIC_GOV 0.94 (support 950), TOPIC_LAW 0.74 (68), TOPIC_MEDIA 0.73 (58), TOPIC_ECON_SERV 0.60 (37), TOPIC_FOR 0.52 (40)
- **Worth your attention (not acted on in Phase 2):** TOPIC_ECON_SERV and TOPIC_FOR have the weakest per-class F1, consistent with them being the smallest, most heavily oversampled classes (both floored at 400 training examples per the data-prep notebook)
- **What is NOT verified:** same caveats as Layer 1

## Layer 4 — Stance

- **Base model:** `xlm-roberta-base`
- **Labels:** `STANCE_CRIT: 0, STANCE_NEUT: 1, STANCE_SUPP: 2` — reported by the notebook, exactly matches this repo's Phase 1 `label_map.json`
- **Input column:** `text_clean`, `max_seq_length: 256`
- **Artifacts the notebook reports writing:** same pattern as Layer 2, including `class_weights.json` consumption
- **Reported metrics:** macro-F1 0.86; per-class F1 — STANCE_CRIT 0.95 (support 813), STANCE_NEUT 0.90 (294), STANCE_SUPP 0.75 (46)
- **Worth your attention (not acted on in Phase 2):** STANCE_SUPP precision (0.62) is noticeably lower than its recall (0.93) on a small support (46) — consistent with it being the smallest, most heavily oversampled class (floored at 500 training examples)
- **What is NOT verified:** same caveats as Layer 1

## What is required before Phase 4 (inference integration) can honestly begin

1. **Access to the actual checkpoint files.** Either:
   - (a) upload the three `checkpoints/best_model/` directories (or a zip containing them) to this conversation the same way the repository zip was uploaded, or
   - (b) connect a tool in this environment that can read the Google Drive folder directly, or
   - (c) push the checkpoints to Hugging Face Hub (the repo's own documented plan — `huggingface_hub_repo` fields are still unfilled placeholders) and share the real repo IDs.
2. Once accessible, each checkpoint should be loaded with `AutoModelForSequenceClassification.from_pretrained()` / `AutoTokenizer.from_pretrained()`, its `num_labels`/output shape confirmed against this repo's corrected `config.json`, and a minimal smoke test run on a small set of synthetic (non-user) example sentences per language (Sinhala/Singlish/English) — at which point, and only then, `checkpoint_status` can honestly become `AVAILABLE_AND_VERIFIED`.
3. This environment currently lacks `torch`, `transformers`, and `sentencepiece` — noted for completeness, not installed, since there is nothing to load yet and installing them now would serve no purpose.

## Dependency / environment notes

- `pip show torch transformers sentencepiece` → none installed in this sandbox.
- No `.safetensors`, `.bin`, `trainer_state.json`, or any other HF-format artifact exists anywhere in the repository, in the uploaded repository zip, or in any file directly shared in this conversation — confirmed by a full filesystem search, not assumed.

## Phase 4 update — model integration status

The model wrapper classes, config-driven factory, and cascade
(`src/public_pulse/models/`, `src/public_pulse/inference/cascade.py`) are
now fully implemented against the contracts above. This section records
what Phase 4 actually verified, split deliberately into two categories
per the phase's own instructions — these must never be merged into a
single "model verified" claim:

**A. Implementation / contract (real code, real tests, no fabrication):**
- `BaseClassifier.load()` distinguishes three real failure modes:
  `CheckpointNotFoundError` (configured path doesn't exist),
  `MissingDependencyError` (torch/transformers not importable), and
  `ModelLoadError` (path exists, load attempted, artifact invalid or
  output-head shape mismatched against the label map).
- Checkpoint paths are configuration-driven (`configs/layerN.yaml`), with
  per-layer environment variable overrides (e.g.
  `PUBLIC_PULSE_LAYER1_CHECKPOINT_PATH`) — nothing hard-codes the Google
  Drive path the notebooks reported.
- The cascade (`InferenceCascade`) never calls Layer 2/Layer 4 for a
  Layer 1 NOISE prediction — verified down to "never invoked at all" for
  an all-NOISE batch, not just "result discarded."
- Layer 1 receives `text_raw` unmodified; Layer 2/Layer 4 receive
  `text_clean` — verified by inspecting exactly what each fake classifier
  was called with, not inferred from output.
- Models are loaded at most once per classifier instance; repeated
  `predict()` calls do not reload.
- 40 new tests (`tests/test_models.py`, `tests/test_cascade.py`) plus 4
  integration-sanity tests (`tests/test_inference.py`) — all passing.

**B. Real artifact verification (genuinely, not a simulation — this
environment's real current state):**
- `build_classifier("layer1"/"layer2"/"layer4")` + `.load()` **really
  does** raise `CheckpointNotFoundError` right now, for real, because
  this repository genuinely has no checkpoint files on disk. This is not
  a mocked test of a hypothetical failure — it is the actual behavior of
  the actual code against the actual (empty) checkpoint directories.
- Pointing a classifier at a directory that exists (via the env-var
  override) but installing no ML framework **really does** raise
  `MissingDependencyError`, because torch/transformers genuinely are not
  installed in this sandbox.
- **No real model was loaded. No real prediction was produced. No
  smoke test against real weights was run.** Checkpoint status for all
  three layers remains `ACCESS_UNAVAILABLE` — this phase did not, and
  could not, change that. Nothing here upgrades any layer to
  `AVAILABLE_AND_VERIFIED`.

**What would be required to actually run inference:** the same three
options recorded above (upload the checkpoint directories, connect a
Drive-capable tool, or share real Hugging Face Hub repo IDs), plus
installing `torch` and `transformers` in whatever environment ends up
running inference — neither was done here, since there is currently
nothing for those packages to load.
