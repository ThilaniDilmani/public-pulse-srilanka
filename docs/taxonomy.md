# Public Pulse — Classification Taxonomy

**Active model architecture: Layer 1 → Layer 2 → Layer 4.**
There is no Layer 3. The numbering (1, 2, 4) is kept intentionally to
preserve the research project's history; it is not a typo.

Authoritative source for every contract below: the six final training
notebooks (`01_data_preparation.ipynb`, `02_training.ipynb`,
`layer2_01_data_preparation_final.ipynb`, `layer2_02_training_final.ipynb`,
`layer4_01_data_preparation_final.ipynb`, `layer4_02_training_final.ipynb`).

## Layer 1 — Utility / Gatekeeper

`layer1_utility_label`: **VALID, NOISE** (2 classes)

- Model input: `text_raw` (uncleaned comment text)
- max_seq_length: 256
- No `SPAM` class. Early cascade exit occurs on `NOISE` only.

## Layer 2 — Macro Topic

`layer2_topic_label`: **TOPIC_ECON_SERV, TOPIC_FOR, TOPIC_GOV, TOPIC_LAW, TOPIC_MEDIA** (5 classes)

- Model input: `text_clean` (see preprocessing contract below)
- max_seq_length: 256

## Layer 4 — Stance

`layer4_stance_label`: **STANCE_CRIT, STANCE_NEUT, STANCE_SUPP** (3 classes)

- Model input: `text_clean`
- max_seq_length: 256
- `NULL` is not a model target.

## Preprocessing contract

| Layer | Input column | Cleaning applied |
|---|---|---|
| Layer 1 | `text_raw` | None — raw text used as-is |
| Layer 2 | `text_clean` | Unicode NFC normalization, zero-width character removal, URL → `[URL]`, whitespace collapse. No lowercasing, no punctuation removal (deliberate -- both carry signal). |
| Layer 4 | `text_clean` | Same as Layer 2 |

Both `text_raw` and `text_clean` must be preserved per comment in the
production pipeline, since different layers require different variants.

**Implementation status (Phase 3):** this contract is implemented in
`src/public_pulse/preprocessing/text_cleaning.py` (`clean_text()` for
Layer 2/4, `get_layer1_input()` for Layer 1, `build_text_variants()` for
ETL to persist both per comment), ported verbatim from the notebooks and
verified against real before/after examples from the notebooks' own
executed output. This is a preprocessing implementation only -- it does
not mean model inference is operational. Layer 1/2/4 inference itself is
Phase 4 work and remains blocked on checkpoint access (see
`docs/MODEL_REGISTRY.md`).

**Implementation status (Phase 4):** the model wrapper classes
(`src/public_pulse/models/layer1.py`, `layer2.py`, `layer4.py`), the
config-driven factory (`src/public_pulse/models/factory.py`), and the
`layer1 -> layer2 -> layer4` cascade (`src/public_pulse/inference/cascade.py`)
are fully implemented and unit-tested (cascade routing logic verified
with test doubles; real checkpoint-failure paths verified against this
environment's actual, genuine current state -- no fabricated weights or
mocked "success"). **Real, checkpoint-backed inference is still blocked**:
every layer's status remains `ACCESS_UNAVAILABLE` per Phase 2, and
calling `InferenceCascade.from_config().predict(...)` today correctly
raises `CheckpointNotFoundError` rather than silently falling back to an
untrained base model. Do not read "Phase 4 complete" as "inference is
operational" -- see `docs/MODEL_REGISTRY.md` for exactly what remains
blocked and why.

## Changelog — taxonomy corrections (Phase 1, repository correction pass)

The taxonomy documented above is final and authoritative. Earlier stages
of this research project used different, since-superseded taxonomies.
This section is a historical record, not an active specification —
none of the items below are valid model outputs.

- **Layer 3 (fine-grained sub-issue) was removed.** Real-world label
  coverage for sub-issue tags was too sparse (~7% of the dataset,
  most individual sub-issue classes under 60 labeled examples) to
  train a reliable classifier in this phase of the research. This was
  a documented scope decision, not an oversight, and Layer 3 is not
  planned to be reintroduced.
- **Layer 1's `SPAM` class was removed.** The final taxonomy uses
  `VALID`/`NOISE` only; noise-vs-spam was judged not reliably
  separable at annotation time and was folded into `NOISE`.
- **Layer 2's `TOPIC_ECON` and `TOPIC_SERV` were merged into
  `TOPIC_ECON_SERV`.** Both original classes individually fell below
  the project's minimum-examples-per-class threshold for reliable
  training even after oversampling.
- **Layer 4's `STANCE_CRIT_DIR` and `STANCE_CRIT_SARC` were merged
  into `STANCE_CRIT`.** The direct-criticism-vs-sarcasm distinction
  is deferred to a possible future research iteration; the current
  model does not attempt to separate them. An `is_sarcastic`
  auxiliary signal (emoji/punctuation-based) was explored during data
  preparation as a research note, not shipped as a model output.
- **Layer 4's `NULL` class was removed.** It was never populated with
  labeled examples and was not a real model target.
