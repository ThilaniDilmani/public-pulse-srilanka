# Public Pulse — YouTube Data API v3 Extraction Architecture (Phase 6)

**Status: IMPLEMENTED (Phase 6)**
**Active ML architecture: Layer 1 → Layer 2 → Layer 4. There is no Layer 3.**

---

## Overview

The extraction system collects public YouTube channel metadata, program definitions, videos, comment threads, and replies using the YouTube Data API v3 and persists them into PostgreSQL via the Phase 5B database repository layer (`upsert_channel`, `upsert_program`, `upsert_video`, `upsert_comment`).

```
YouTube Data API v3
       │
       ▼
Extraction Package (src/public_pulse/extraction/)
  ├── Config Loader (configs/programs.yaml + YOUTUBE_API_KEY)
  ├── YouTube Client (retries, rate-limits, error handling)
  ├── Video Discovery (playlist vs channel fallback)
  ├── Comment Fetcher (threads, replies, comments-disabled handling)
  ├── Parsers & Privacy Hasher (HMAC-SHA256 author_hash, raw text)
  └── Extraction Service & CLI (PipelineRun audit tracking)
       │
       ▼
Phase 5B Repository Layer
       │
       ▼
PostgreSQL / SQLite Database
```

---

## Target Programs Configuration (`configs/programs.yaml`)

The 14 target programs defined in `configs/programs.yaml` come strictly from the project PDF reference.

| # | Program Name | Channel ID | Playlist ID | Discovery Strategy |
|---|---|---|---|---|
| 1 | `bai thakshalawa` | `UCKQo4WI1lxhygYrrSo5TkuQ` | `PL8m5cFsG6joS___AwyttjIsBy1cs3nLMK` | PLAYLIST |
| 2 | `Hiru Salakuna (Hiru)` | `UCckltLEhFLv8Xz_lQhYfwmg` | `PLdKFCUSuUa1ZjTqcN8mmAzBjQOKnQ2Wmp` | PLAYLIST |
| 3 | `Derana 360 (Derana)` | `UCCK3OZi788Ok44K97WAhLKQ` | `PLkkCdeu97j3C1k9B3UcGVBlEEIl5Sjk91` | PLAYLIST |
| 4 | `Truth with Chamuditha` | `UCfdBd-9WWZUv1h7d80Omy8g` | *None* (`null`) | CHANNEL_TITLE_MATCH |
| 5 | `Hari TV - Lahiru Mudalige` | `UC0RX5hQE6UpHTjfub4NZSPg` | *None* (`null`) | CHANNEL_TITLE_MATCH |
| 6 | `Hiru Balaya (Hiru)` | `UCckltLEhFLv8Xz_lQhYfwmg` | `PLdKFCUSuUa1apqRDuj7DesaDF-7h_Bm3D` | PLAYLIST |
| 7 | `Sirasa Satana` | `UCgnFSj7jQffD5V5m05j4dPw` | `PLwBEINflt3JGKH1zzFy3mgu29ahrB3maJ` | PLAYLIST |
| 8 | `Sudaa creation` | `UC3tvYy-s84yySG7V85jRDnA` | *None* (`null`) | CHANNEL_TITLE_MATCH |
| 9 | `Wada pitiyaa (Ada derana)` | `UCCK3OZi788Ok44K97WAhLKQ` | `PLkkCdeu97j3CM896xOXvIZsVp49HZ2Oe7` | PLAYLIST |
| 10 | `Sirasa dawasa` | `UCgnFSj7jQffD5V5m05j4dPw` | `PLwBEINflt3JHmzxrEoMD7bzA8Lo5yfSRc` | PLAYLIST |
| 11 | `Rathu ira (Swarnawahini)` | `UCcijXxFzSXgoM6q9cCtT9PA` | `PLiPJeymWD44MdfLc7W_9sYE6RbxW77kSM` | PLAYLIST |
| 12 | `Paththare visthare (Hiru News)` | `UCckltLEhFLv8Xz_lQhYfwmg` | `PLdKFCUSuUa1bak-Y3w8rIL9PFO9gBTEfD` | PLAYLIST |
| 13 | `Hiru news 6.55pm (Hiru newa)` | `UCckltLEhFLv8Xz_lQhYfwmg` | `PLdKFCUSuUa1aBMMrERhD2ONKi0Nc0DLDu` | PLAYLIST |
| 14 | `Ada derana 6.55 (Ada derana)` | `UCCK3OZi788Ok44K97WAhLKQ` | `PLkkCdeu97j3DDsSAG866tOV9O54doYEst` | PLAYLIST |

*Note:* `program_type` remains `null` for all programs.

---

## Shared Channel Architecture

Several programs share the same YouTube channel. The database maintains **exactly ONE `Channel` record** per unique YouTube channel ID, while creating separate `Program` records referencing that channel ID:

- `UCckltLEhFLv8Xz_lQhYfwmg`: 4 programs (Hiru Salakuna, Hiru Balaya, Paththare visthare, Hiru news 6.55pm)
- `UCCK3OZi788Ok44K97WAhLKQ`: 3 programs (Derana 360, Wada pitiyaa, Ada derana 6.55)
- `UCgnFSj7jQffD5V5m05j4dPw`: 2 programs (Sirasa Satana, Sirasa dawasa)

---

## Raw Text Preservation Contract

The extraction module preserves the raw YouTube comment string into `text_raw` without any NLP preprocessing.

- No lowercasing
- No emoji removal
- No punctuation stripping
- No Sinhala transliteration
- No stop-word removal or stemming

Phase 7 ETL will handle NLP cleaning for `text_clean`.

---

## Privacy & Pseudonymization

Author channel IDs are converted into a stable pseudonymous hash (`author_hash`) using HMAC-SHA256 (or SHA-256 fallback). Individual user names and raw author channel IDs are never stored or exposed.

---

## Command Line Interface (CLI)

```powershell
# Extract all configured programs (with limits)
venv\Scripts\python.exe -m public_pulse.extraction.service --all --limit-videos 2 --limit-comments 50

# Extract single program
venv\Scripts\python.exe -m public_pulse.extraction.service --program "Hiru Salakuna (Hiru)" --limit-videos 1 --limit-comments 20

# Dry-run mode (no DB commit)
venv\Scripts\python.exe -m public_pulse.extraction.service --all --dry-run
```

---

## Testing

```powershell
# Run extraction unit tests (25 tests)
venv\Scripts\python.exe -m pytest tests/test_extraction.py -v

# Run full project test suite (157 total tests)
venv\Scripts\python.exe -m pytest tests/ -v

# Optional live API smoke test (requires YOUTUBE_API_KEY)
venv\Scripts\python.exe scripts/smoke_test_youtube_extraction.py
```
