# Phase 12A — Dashboard Pre-Implementation Audit & UX Architecture Report
## Public Pulse

**Status:** AUDIT ONLY — No implementation performed  
**Baseline:** 276/276 tests passing (Phases 1–11 complete)  
**Author:** Phase 12A Audit  
**Date:** 2026-09-08

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Frontend State](#2-current-frontend-state)
3. [Verified Backend/API Capabilities](#3-verified-backendapi-capabilities)
4. [React + Vite vs Streamlit Decision](#4-react--vite-vs-streamlit-decision)
5. [Recommended Frontend Architecture](#5-recommended-frontend-architecture)
6. [Information Architecture](#6-information-architecture)
7. [Page-by-Page UX Specification](#7-page-by-page-ux-specification)
8. [Global Filter Architecture](#8-global-filter-architecture)
9. [Analytics Specification](#9-analytics-specification)
10. [Temporal Analysis Specification](#10-temporal-analysis-specification)
11. [Public Pulse Moments — Feasibility](#11-public-pulse-moments--feasibility)
12. [AI Intelligence UX](#12-ai-intelligence-ux)
13. [Evidence Drill-Down UX](#13-evidence-drill-down-ux)
14. [Faithfulness UX](#14-faithfulness-ux)
15. [Data Quality UX](#15-data-quality-ux)
16. [Collection Status Feasibility](#16-collection-status-feasibility)
17. [API → UI Mapping Table](#17-api--ui-mapping-table)
18. [Missing API Capabilities](#18-missing-api-capabilities)
19. [Design System](#19-design-system)
20. [Chart Strategy](#20-chart-strategy)
21. [State Management](#21-state-management)
22. [Performance Architecture](#22-performance-architecture)
23. [Security & Privacy Architecture](#23-security--privacy-architecture)
24. [Accessibility](#24-accessibility)
25. [Testing Strategy](#25-testing-strategy)
26. [Deployment Architecture](#26-deployment-architecture)
27. [Proposed Frontend Folder Structure](#27-proposed-frontend-folder-structure)
28. [Dependency Recommendations](#28-dependency-recommendations)
29. [Implementation Phases — 12B / 12C / 12D](#29-implementation-phases--12b--12c--12d)
30. [Risks and Mitigations](#30-risks-and-mitigations)
31. [Files That Would Be Created/Modified](#31-files-that-would-be-createdmodified)
32. [Final Go/No-Go Recommendation](#32-final-gono-go-recommendation)

---

## 1. Executive Summary

Public Pulse has a complete analytical backend (Phases 1–11). The Phase 11 FastAPI application exposes 30+ endpoints delivering server-side aggregated analytics, grounded AI insights, faithfulness verification, and a full evidence chain. All data is pre-scored; the dashboard performs zero inference.

The frontend task is to **present** this analytical engine — not to replicate it. The dashboard must be a civic intelligence interface capable of answering the twelve discourse questions stated in the project brief, grounded strictly in what the API actually provides.

**Key finding from this audit:** The API is analytically sufficient to build a high-value dashboard. One structural gap exists: the analytics endpoints do not yet accept `start_date`/`end_date` query parameters at the HTTP layer (the service layer supports them, but the route signatures omit them). This single gap blocks full date-range filtering and must be remedied before Phase 12B begins (see §18).

**Recommendation: React + Vite.** Build Phase 12 as a standalone React single-page application. The existing Streamlit stub (`dashboard/app.py`) should be retained as a placeholder but replaced by a dedicated `dashboard/` React workspace.

---

## 2. Current Frontend State

### What exists

| File | State |
|---|---|
| `dashboard/app.py` | 9-line Streamlit stub. Displays title and one line. No data connection. |
| `dashboard/components/__init__.py` | Empty |
| `dashboard/components/program_compare.py` | 47 bytes — empty stub |
| `dashboard/components/sentiment_tracker.py` | 56 bytes — empty stub |
| `dashboard/components/topic_meter.py` | 39 bytes — empty stub |
| `dashboard/components/sarcasm_view.py` | 938 bytes — Streamlit component referencing removed Layer 3 concepts (sarcasm was merged into STANCE_CRIT). **Must NOT be carried forward.** |

### Assessment

There is **no production frontend**. The Streamlit stub is a placeholder with no analytical value. `sarcasm_view.py` references superseded taxonomy and must not be used. Phase 12 starts from scratch.

---

## 3. Verified Backend/API Capabilities

The following is verified by reading the actual source, not assumed from documentation.

### 3.1 Confirmed working endpoints

**Health**
- `GET /health` — returns `status`, `phases_complete`, `active_architecture`, `subissue_status`, `database`
- `GET /` — root health check at top level

**Catalog** (Channel → Program → Video hierarchy preserved)
- `GET /api/v1/channels` → `List[ChannelOut]`  
  Fields: `id, name, channel_url, description, subscriber_count, created_at`
- `GET /api/v1/channels/{id}` → `ChannelOut`
- `GET /api/v1/channels/{id}/programs` → `List[ProgramOut]`
- `GET /api/v1/programs` → `List[ProgramOut]` (filterable by `channel_id`, `is_active`)  
  Fields: `id, channel_id, channel_name, name, platform, is_active, created_at`  
  **Note: `program_type` is always `null` — do not display it**
- `GET /api/v1/programs/{id}` → `ProgramOut`
- `GET /api/v1/programs/{id}/videos` → `List[VideoOut]` (paginated, limit/offset)  
  Fields: `id, program_id, title, published_at, duration_seconds, is_live, comment_count, scraped_at`

**Analytics (all return pre-aggregated server-side data)**
- `GET /api/v1/analytics/overview` → `OverviewKPIOut`  
  Fields: `total_comments, valid_comments, noise_comments, pending_comments, noise_rate, total_videos, total_programs, total_channels, avg_comments_per_video`  
  Scope filters: `program_id, channel_id, video_id`  
  ⚠️ **Date range: NOT yet on route signature — gap, see §18**

- `GET /api/v1/analytics/topics` → `TopicDistributionOut`  
  Fields: `program_id, channel_id, video_id, start_date, end_date, total_valid_comments, distribution[{topic, count, percentage}]`  
  ⚠️ **Date range: NOT on route signature**

- `GET /api/v1/analytics/stances` → `StanceDistributionOut`  
  Fields: `distribution[{stance, count, percentage}]`, `topic_filter`, scope fields  
  ⚠️ **Date range: NOT on route signature**

- `GET /api/v1/analytics/topic-stance-matrix` → `TopicStanceMatrixOut`  
  Fields: `matrix: { topic → { stance → count } }`

- `GET /api/v1/analytics/entity-matrix` → `EntityMatrixOut`  
  `entity_type`: `program` | `channel`; `matrix_type`: `topic` | `stance`  
  Returns: `matrix: { entity_name → { label → count } }`

- `GET /api/v1/analytics/volume-over-time` → `VolumeOverTimeOut`  
  `granularity`: `daily` | `weekly` | `monthly` only (not hourly/quarterly/yearly — see §18)  
  Fields: `data_points[{date, total_comments, valid_comments, noise_comments}]`

- `GET /api/v1/analytics/period-over-period` → `PeriodOverPeriodOut`  
  `period_days`: 1–365  
  Fields: `period_days, current_period: Dict, previous_period: Dict, changes: Dict`

- `GET /api/v1/analytics/episodes` → `VideoAnalyticsOut`  
  Fields: `items[{video_id, title, program_name, published_at, total_comments, valid_comments, noise_rate, top_topic, stance_breakdown}]`, `total`

- `GET /api/v1/analytics/data-quality` → `DataQualityAnalyticsOut`  
  Fields: `overview: Dict, average_confidence_by_layer: Dict[str, float], subissue_status: str`

- `GET /api/v1/analytics/faithfulness` → `FaithfulnessAnalyticsOut`  
  Fields: `total_verifications, mean_grounding_score, mean_claim_support_rate, mean_contradiction_rate`  
  ⚠️ **Missing: `mean_partial_support_rate`, `mean_unsupported_claim_rate`, `mean_citation_precision` — see §18**

**Program-scoped analytics**
- `GET /api/v1/programs/{id}/analytics/overview`
- `GET /api/v1/programs/{id}/analytics/topics`
- `GET /api/v1/programs/{id}/analytics/stances`
- `GET /api/v1/programs/{id}/analytics/topic-stance-matrix`
- `GET /api/v1/programs/{id}/analytics/volume-over-time`
- `GET /api/v1/programs/{id}/insights`

**Evidence**
- `POST /api/v1/evidence/retrieve` → `EvidencePayloadOut`  
  Body: `top_k, topic, stance, program_id, channel_id, start_date, end_date, keywords[]`  
  Returns: `evidence_set_id, retrieved_at, evidence_count, total_matching_count, retrieval_method, evidence_items[]`  
  Each item: `rank, evidence_id, comment_id, text_clean, posted_at, video_id, video_title, program_name, channel_name, layer2_topic, layer2_confidence, layer4_stance, layer4_confidence, like_count, relevance_score`  
  **Privacy: `author_hash` and `text_raw` are excluded by schema**

**Insights**
- `POST /api/v1/insights/generate` → `JobStatusOut` (202 Accepted)  
  Body: `evidence_set_id, program_id (optional)`
- `GET /api/v1/insights` → `List[InsightOut]` (filterable by `program_id`, `generation_status`)
- `GET /api/v1/insights/{id}` → `InsightOut`  
  Fields: `insight_id, evidence_set_id, program_id, insight_type, generation_status, summary, findings[], discourse_interpretation, limitations, uncertainty_note, llm_provider, llm_model, prompt_version, generated_at, evidence_count_used, stance_distribution, error_message`  
  Each finding: `finding_id, text, evidence_ids[], confidence`

**Verification**
- `POST /api/v1/insights/{id}/verify` → `JobStatusOut` (202 Accepted)
- `GET /api/v1/insights/{id}/verification` → `VerificationReportOut`  
  Fields: `verification_id, insight_id, evidence_set_id, claim_support_rate, partial_support_rate, unsupported_claim_rate, contradiction_rate, grounding_score, evidence_citation_precision, total_claims_evaluated, claim_verifications[], verifier_method, verifier_model, verified_at`  
  Each claim: `claim_id, finding_id, claim_text, label (SUPPORTED|PARTIALLY_SUPPORTED|UNSUPPORTED|CONTRADICTED), evidence_ids[], verification_method, reason`

**Jobs**
- `GET /api/v1/jobs/{job_id}` → `JobStatusOut`  
  Fields: `job_id, job_type, status (pending|running|completed|error), reference_id, error, created_at, completed_at`

**Legacy / Backwards-compat**
- `GET /api/v1/sentiment` → `StanceDistributionOut`
- `GET /api/v1/topics` → `TopicDistributionOut`
- `GET /api/v1/comments/summary` → `OverviewKPIOut`

### 3.2 Known programs (from `configs/programs.yaml`)

14 programs across at least 6 channels:
- Hiru channel (UCckl...): Hiru Salakuna, Hiru Balaya, Paththare visthare, Hiru news 6.55pm
- Ada Derana channel (UCCK3...): Derana 360, Wada pitiyaa, Ada derana 6.55
- Sirasa channel (UCgnF...): Sirasa Satana, Sirasa dawasa
- Swarnawahini channel (UCcij...): Rathu ira
- Individual channels: Truth with Chamuditha, Hari TV, bai thakshalawa, Sudaa creation

### 3.3 Authoritative taxonomy

**Layer 1 (Utility)**
- `VALID` — usable comment, forwarded to L2/L4
- `NOISE` — filtered out, L2/L4 not run

**Layer 2 (Topic)**
- `TOPIC_ECON_SERV` — Economics & Services
- `TOPIC_FOR` — Foreign Affairs
- `TOPIC_GOV` — Governance
- `TOPIC_LAW` — Law & Justice
- `TOPIC_MEDIA` — Media

**Layer 4 (Stance)**
- `STANCE_CRIT` — Critical (includes former STANCE_CRIT_SARC)
- `STANCE_NEUT` — Neutral
- `STANCE_SUPP` — Supportive

**Layer 3: DOES NOT EXIST. Must never appear in UI.**

---

## 4. React + Vite vs Streamlit Decision

### 4.1 Streamlit

| Aspect | Verdict |
|---|---|
| Setup speed | ✅ Very fast for prototypes |
| Visual quality | ❌ Generic, limited customization |
| Layout control | ❌ Constrained column/grid system |
| Interactivity | ❌ Full page re-runs on interaction; poor for filter cascades |
| URL state / deep linking | ❌ No native URL-driven filter state |
| Custom design system | ❌ Cannot build a true brand identity |
| Async job polling | ❌ No native polling primitive; requires `st.experimental_rerun` workarounds |
| Evidence drill-down | ❌ Modal and slide-panel UX impossible |
| Performance | ❌ All chart data downloaded to browser; no pagination control |
| Production quality | ❌ Looks like a university demo |
| Existing code | ⚠️ 9-line stub exists; not an investment worth preserving |

### 4.2 React + Vite

| Aspect | Verdict |
|---|---|
| Design control | ✅ Full — custom design system, tokens, brand identity |
| Interactivity | ✅ Component-level state; filter cascades without page reruns |
| URL state | ✅ React Router v6 search params for shareable filter states |
| Async polling | ✅ `setInterval` + React Query for clean job polling |
| Evidence drill-down | ✅ Proper slide panels, modals, nested navigation |
| Performance | ✅ Lazy loading, code splitting, virtualization, pagination |
| Accessibility | ✅ Full a11y control |
| Ecosystem | ✅ Recharts/Nivo/Victory for charts; Tailwind for styling |
| Build output | ✅ Static bundle — deployable to Netlify, Vercel, HF Spaces, Docker |
| Dev speed | ✅ HMR, TypeScript, excellent tooling |
| Complexity | ⚠️ Requires more initial setup than Streamlit |

### 4.3 Decision

**React + Vite is the recommended choice.**

The existing `streamlit>=1.35` dependency in `pyproject.toml` should remain for now (it does not conflict). The new frontend will live in `dashboard/` as a React/Vite workspace, replacing the Python Streamlit stub.

---

## 5. Recommended Frontend Architecture

```
dashboard/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
├── .env.local               # VITE_API_BASE_URL, VITE_API_KEY
├── public/
│   └── favicon.svg          # Public Pulse logo
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── api/                 # API client layer (typed, no raw fetch in components)
    ├── components/          # Shared UI components (cards, charts, filters)
    ├── features/            # Page-level feature modules
    ├── hooks/               # Custom React hooks (useFilterState, useJobPoll, etc.)
    ├── lib/                 # Utilities, formatters, constants
    ├── store/               # Global filter store (Zustand)
    ├── styles/              # CSS variables / Tailwind config
    └── types/               # TypeScript API response types (generated from OpenAPI)
```

**TypeScript throughout.** Types generated from the OpenAPI schema at `/api/openapi.json` using `openapi-typescript`. This ensures type safety against the actual Phase 11 contract without manual duplication.

**No direct database access.** The frontend speaks only to `VITE_API_BASE_URL`. The API is the only data source.

---

## 6. Information Architecture

### Navigation Structure

```
Public Pulse
├── Overview                    ← Landing page, high-level discourse snapshot
├── Explore
│   ├── Volume & Trends         ← Discussion volume over time + P-o-P
│   ├── Topics                  ← Topic distribution, ranking, trends
│   ├── Stance                  ← Stance distribution (filtered by topic)
│   └── Topic × Stance          ← Cross-tabulation matrix / heatmap
├── Sources
│   ├── Channels                ← Channel list + per-channel summary
│   ├── Programs                ← Program list + per-program deep dive
│   └── Episodes                ← Episode/video analytics table
├── AI Intelligence
│   ├── Insights                ← Generated insights with findings
│   ├── Evidence Explorer       ← Evidence drill-down (insight → finding → comment)
│   └── Faithfulness            ← Verification reports + analytics
└── Data
    ├── Data Quality            ← Pipeline quality indicators
    ├── Collection Status       ← What can be shown (see §16)
    └── Methodology             ← Static explanatory page
```

### Why each page exists

| Page | Justification |
|---|---|
| **Overview** | Entry point; users need a quick discourse snapshot before drilling down |
| **Volume & Trends** | Core civic question: how much is being said and how is it changing? |
| **Topics** | Which issues dominate? Ranked by volume. |
| **Stance** | How do commenters feel? Critical/Neutral/Supportive breakdown. |
| **Topic × Stance** | The key cross-analysis — does stance differ by topic? |
| **Channels** | Source-level comparison; different channels reach different audiences |
| **Programs** | The most granular useful source unit; 14 programs are the atomic analysis unit |
| **Episodes** | Specific video events that may drive spikes |
| **Insights** | AI-generated discourse summaries with evidence grounding |
| **Evidence Explorer** | Allows users to verify AI claims against real comments |
| **Faithfulness** | Transparency about AI reliability — essential for civic credibility |
| **Data Quality** | Informs interpretation; users must understand noise/validity rates |
| **Collection Status** | Partial — see §16 for what is and is not possible |
| **Methodology** | Static page explaining classification model, privacy policy, taxonomy |

---

## 7. Page-by-Page UX Specification

### 7.1 Overview Page

**Purpose:** Answer "what is happening right now in public discourse?"

**Header KPI Strip (from `GET /api/v1/analytics/overview`)**
```
┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ Total Comments   │ Valid Comments   │ Noise Rate       │ Avg / Episode    │
│ [total_comments] │ [valid_comments] │ [noise_rate %]   │ [avg_comments_   │
│                  │                  │                  │  per_video]      │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┘
```
Each KPI card shows:
- Primary metric (large, bold)
- Context label beneath
- Scope indicator ("All Programs", "Hiru Salakuna", etc. based on global filter)
- No change arrows until date range filter is wired (§18 gap resolved)

**Mini-charts row**
- Topic distribution: horizontal ranked bar (compact, 5 bars for 5 topics)
- Stance distribution: donut (3 slices: CRIT/NEUT/SUPP)
- Volume sparkline: last 30-day daily trend

**Topic × Stance Highlights (from `GET /api/v1/analytics/topic-stance-matrix`)**
- 5×3 color-coded grid; each cell shows count
- Highlight highest-count cell (dominant signal)
- Caption: "Among [N] valid comments within the selected scope..."

**Top Programs (from `GET /api/v1/analytics/entity-matrix?entity_type=program&matrix_type=topic`)**
- Ranked bar chart: top 5 programs by total valid comment volume
- Hover: shows topic breakdown

**Period-over-Period Summary (from `GET /api/v1/analytics/period-over-period`)**
- Shows last 30 days vs previous 30 days
- Three change indicators: volume change %, top topic shift, stance shift
- Label clearly: "Compared with the preceding 30-day period"

**Recent AI Insights strip (from `GET /api/v1/insights?limit=3`)**
- Latest 3 insights as cards
- Shows: insight type, program, generation status, summary (truncated to 2 lines)
- "View all" → `/ai/insights`

**Faithfulness Summary (from `GET /api/v1/analytics/faithfulness`)**
- Mean grounding score (gauge or percentage)
- Mean CSR badge
- "Based on [N] verified insights"

**Empty states:**
- No data yet: "No analyzed comments in this scope. Adjust filters or check collection status."
- No insights yet: "AI insights not yet generated. Navigate to AI Intelligence to generate."

---

### 7.2 Explore — Volume & Trends

**Primary chart: Volume over time**
- `GET /api/v1/analytics/volume-over-time?granularity={granularity}`
- Granularity selector: Daily | Weekly | Monthly
- Area chart: total_comments (light fill) with valid_comments (solid line) overlaid
- Noise floor shown as bottom fill (total - valid)
- Hover tooltip: date, total, valid, noise count

**Period-over-Period panel**
- `GET /api/v1/analytics/period-over-period?period_days={N}`
- Period selector: 7 / 14 / 30 / 60 / 90 days
- Table showing current vs previous period for: total_comments, valid_comments, noise_rate
- Change column with ↑↓ arrows and percentage

**Scope:** All global filters apply (channel/program). Video-level volume supported via `video_id` param.

**⚠️ NOT CURRENTLY SUPPORTED:** Hourly granularity, quarterly, yearly, custom date range. Route only accepts `daily|weekly|monthly` (see §18).

---

### 7.3 Explore — Topics

**Topic distribution bar chart**
- `GET /api/v1/analytics/topics`
- Horizontal ranked bars, longest first
- Each bar: label (human-readable, see §9.1), count, percentage
- Color-coded by topic (consistent color tokens)

**Topic trend over time**
- NOT DIRECTLY SUPPORTED by a single endpoint — see §18
- Workaround: NOT recommended (would require multiple calls and client-side merging)
- Mark as **future enhancement**

**Program comparison (entity matrix)**
- `GET /api/v1/analytics/entity-matrix?entity_type=program&matrix_type=topic`
- Grouped bar chart: programs on X-axis, bars per topic
- Toggle: absolute counts vs percentage within program

**Topic cards**
- One card per topic (5 total)
- Shows: label, count, share %, definition excerpt

---

### 7.4 Explore — Stance

**Stance distribution donut**
- `GET /api/v1/analytics/stances?topic_filter={optional}`
- Three segments: STANCE_CRIT (red), STANCE_NEUT (grey), STANCE_SUPP (green)
- Center text: total valid comments
- Topic filter dropdown: "All Topics" + 5 topic options
- Labels use readable names (see §9.2)

**Stance by program (entity matrix)**
- `GET /api/v1/analytics/entity-matrix?entity_type=program&matrix_type=stance`
- Stacked bar: each bar is one program, segments are stance proportions

**Important note in UI:**
> "Stance reflects the orientation of comments toward the subject matter, not political affiliation. STANCE_CRIT indicates critical orientation; sarcasm is not separately tracked."

---

### 7.5 Explore — Topic × Stance

**Core heatmap**
- `GET /api/v1/analytics/topic-stance-matrix`
- 5 rows (topics) × 3 columns (stances)
- Cell: count + optional percentage
- Color scale: white → topic accent color (darker = higher count)
- Hover: topic label, stance label, count, % of row, % of column

**Matrix controls**
- Toggle: absolute counts vs row-percentage vs column-percentage
- Highlight mode: highest in row / highest in column

**Interpretation panel**
- Auto-generated caption: "The most common combination within the selected scope is [topic] × [stance] with [N] comments ([%] of valid comments)."

---

### 7.6 Sources — Channels

**Channel list** (`GET /api/v1/channels`)
- Cards, not a table (channels have names, URLs, subscriber counts)
- Each card: channel name, subscriber count (if available), number of programs
- Click → channel detail page

**Channel detail**
- Header: channel name, description, subscriber count
- Programs hosted (`GET /api/v1/channels/{id}/programs`)
- KPI overview scoped to channel (`GET /api/v1/analytics/overview?channel_id={}`)
- Topic distribution chart scoped to channel

---

### 7.7 Sources — Programs

**Program list** (`GET /api/v1/programs`)
- Table with columns: Program name, Channel, Active, Platform, Created
- Filter by channel dropdown
- Row click → Program detail

**Program detail page** — the richest source view
- Header: program name, channel badge, active status
- Analytics tabs:
  - **Overview** — KPIs (`/programs/{id}/analytics/overview`)
  - **Topics** — topic distribution chart (`/programs/{id}/analytics/topics`)
  - **Stance** — stance donut + topic filter (`/programs/{id}/analytics/stances`)
  - **Topic × Stance** — matrix (`/programs/{id}/analytics/topic-stance-matrix`)
  - **Volume** — trend chart (`/programs/{id}/analytics/volume-over-time`)
  - **AI Insights** — insight cards (`/programs/{id}/insights`)
  - **Episodes** — episode table (from cross-scope `/analytics/episodes?program_id={}`)

**Important UX rule:** The program name and channel name are always shown together. A program is never presented as if it *is* the channel.

---

### 7.8 Sources — Episodes

**Episode analytics table** (`GET /api/v1/analytics/episodes`)
- Paginated (20 per page, limit/offset)
- Columns: Title (truncated), Program, Published Date, Total Comments, Valid Comments, Noise Rate, Top Topic, Stance Breakdown (mini stacked bar)
- Sortable by: published date (default desc), total comments, noise rate
- Filter by: program_id, channel_id
- Row click → episode detail (shows video-scoped KPIs using `video_id` filter)

---

### 7.9 AI Intelligence — Insights

**Insight list** (`GET /api/v1/insights`)
- Cards sorted by `generated_at` desc
- Each card: insight type badge, program context, generation status pill, summary snippet
- Filter by: program, generation_status
- Click → Insight detail

**Insight detail**
- Header: type badge, program badge, period (if set), generation metadata (LLM model/version)
- **Summary section:** full `summary` text
- **Findings accordion:** each finding expandable
  - Finding text
  - Confidence badge
  - "View Evidence" button → Evidence Explorer for this finding's `evidence_ids`
- **Interpretation panel:** `discourse_interpretation` (if present)
- **Limitations note:** `limitations` and `uncertainty_note` (if present)
- **Verification status banner:** VERIFIED / UNVERIFIED / FAILED
  - If unverified: "Verify Faithfulness" button → POST `insights/{id}/verify` → poll job

**Status pills:**
- `pending` → grey "Pending"
- `running` → blue pulse "Generating…"
- `completed` → green "Complete"
- `error` → red "Failed" + error message (sanitized)

**Generate new insight panel:**
1. User fills: evidence_set_id (from prior retrieval), optional program
2. POST `insights/generate` → 202 → show job card with polling
3. Auto-refresh job status (`GET /jobs/{job_id}`) every 3s until `completed` or `error`
4. On complete: navigate to new insight detail

---

### 7.10 AI Intelligence — Evidence Explorer

*(see §13 for full drill-down UX specification)*

---

### 7.11 AI Intelligence — Faithfulness

*(see §14 for full faithfulness UX specification)*

---

### 7.12 Data — Data Quality

*(see §15 for full data quality UX specification)*

---

### 7.13 Data — Collection Status

*(see §16 for feasibility assessment)*

---

### 7.14 Data — Methodology

**Static page** — no API calls.

Sections:
- What is Public Pulse? (project description, research context)
- Monitored programs (the 14 programs, with channel names, platform)
- Classification system (Layer 1 / Layer 2 / Layer 4 — clearly labeled; Layer 3 noted as permanently removed)
- Taxonomy reference table (all labels, definitions, examples)
- Privacy policy (what is stored, what is never exposed, author anonymization)
- Data limitations (language notes — no language metadata currently available)
- Political neutrality statement
- Evidence and AI methodology summary

---

## 8. Global Filter Architecture

### 8.1 Filter dimensions (confirmed against API)

| Filter | Supported by API | Notes |
|---|---|---|
| Channel | ✅ `channel_id` param | All analytics endpoints |
| Program | ✅ `program_id` param | All analytics + per-program endpoints |
| Video / Episode | ✅ `video_id` param | Overview, topics, stances, matrix, volume |
| Topic | ✅ `topic_filter` param | Stances endpoint only; see §18 for other endpoints |
| Stance | ❌ Not a filter param | NOT CURRENTLY SUPPORTED as a filter |
| Date range (start) | ⚠️ Schema has it | Service layer accepts it; route signature missing — gap |
| Date range (end) | ⚠️ Schema has it | Same gap |
| Granularity | ✅ `granularity` param | volume-over-time only |

**Do NOT implement a stance filter.** The API does not accept it as a query param. **Do NOT implement a date-range filter** until §18 gap is resolved.

### 8.2 Filter state model

```typescript
interface GlobalFilter {
  channelId: string | null;
  programId: string | null;
  videoId: string | null;
  // Reserved for future use after §18 gap resolved:
  // startDate: string | null;
  // endDate: string | null;
}
```

### 8.3 URL synchronization

Filters are stored in URL query params so that pages are shareable and browser navigation works.

```
/explore/topics?channelId=abc&programId=xyz
/sources/programs/xyz/topics
```

React Router v6 `useSearchParams` handles serialization.

### 8.4 Cascading filter rules

1. Selecting a **channel** → program dropdown shows only that channel's programs
2. Selecting a **program** → channel is implied (pre-fill channel from program's `channel_id`)
3. Selecting a **video** → program and channel pre-fill from video's program context
4. Changing channel → **clear** program and video selections

### 8.5 Invalid filter handling

- If a `programId` in URL no longer exists → show "Program not found" banner, reset filter
- If `channelId` and `programId` combination is inconsistent → prioritize `programId`, ignore `channelId`

### 8.6 Reset behavior

- "Clear all filters" button in filter bar → resets to global (all programs, no scope)
- Individual filter has an ×-clear button

### 8.7 Filter persistence

- URL params: active session + shareable
- **No localStorage persistence** — stale filters from previous sessions would mislead users

### 8.8 API request strategy

- Filter changes are **debounced 400ms** before triggering API calls
- All chart queries are invalidated when any filter changes
- React Query handles deduplication: if two charts need the same endpoint with the same params, only one HTTP call is made

### 8.9 Loading behavior

- Skeleton placeholders (not spinners) for all chart panels during load
- KPI cards show `—` while loading
- Charts show a shimmering placeholder matching the chart's approximate dimensions

### 8.10 Interaction between filters and charts

- Every chart title bar shows the active scope: "Hiru Salakuna — Topic Distribution"
- A "scope indicator" chip at the top of every page shows active filters with clear buttons
- When no filter is active: "All Programs — All Channels — All Time"

---

## 9. Analytics Specification

### 9.1 Topic label display names

| API value | Display label |
|---|---|
| `TOPIC_ECON_SERV` | Economics & Services |
| `TOPIC_FOR` | Foreign Affairs |
| `TOPIC_GOV` | Governance |
| `TOPIC_LAW` | Law & Justice |
| `TOPIC_MEDIA` | Media |

These are presentation names only. The API taxonomy is unchanged.

### 9.2 Stance label display names

| API value | Display label | Color token |
|---|---|---|
| `STANCE_CRIT` | Critical | `--color-crit: #C0392B` |
| `STANCE_NEUT` | Neutral | `--color-neut: #7F8C8D` |
| `STANCE_SUPP` | Supportive | `--color-supp: #27AE60` |

**Do NOT label these as "negative / neutral / positive".** They describe orientation toward the subject matter, not valence.

### 9.3 Layer 1 display names

| API value | Display label |
|---|---|
| `VALID` | Valid / Usable |
| `NOISE` | Filtered (Noise) |

### 9.4 Status indicator values

| Job status | Display |
|---|---|
| `pending` | Queued |
| `running` | Processing… |
| `completed` | Complete |
| `error` | Failed |

---

## 10. Temporal Analysis Specification

### 10.1 What is confirmed working

| Granularity | Status |
|---|---|
| `daily` | ✅ Supported |
| `weekly` | ✅ Supported |
| `monthly` | ✅ Supported |
| `hourly` | ❌ NOT SUPPORTED (not in route pattern) |
| `quarterly` | ❌ NOT SUPPORTED |
| `yearly` | ❌ NOT SUPPORTED |
| Custom date range | ❌ NOT SUPPORTED (route gap, §18) |

### 10.2 What to implement in Phase 12B

- Granularity toggle: **Daily / Weekly / Monthly** (matching actual API)
- Period-over-period selector: 7 / 14 / 30 / 60 / 90 days

### 10.3 Future enhancements (document, do not fake)

- Hourly granularity: requires extending route pattern and service layer
- Custom date range: requires adding `start_date`/`end_date` to route signatures (§18)
- Quarterly/yearly: requires extending granularity pattern

---

## 11. Public Pulse Moments — Feasibility

### What "Public Pulse Moments" requires

A Moment must be: **quantitative change + meaningful analytical shift + supporting evidence**

### What the API currently provides

| Requirement | Available? | Source |
|---|---|---|
| Volume data point for any period | ✅ | `volume-over-time` |
| Period-over-period comparison | ✅ | `period-over-period` (returns `changes: Dict`) |
| Top topic per period | ⚠️ Partial | `topics` has no time split |
| Topic shift between periods | ❌ | NOT SUPPORTED |
| Stance shift between periods | ❌ | NOT SUPPORTED |
| Insight explaining a period | ✅ | `insights` (if generated for that period) |
| Evidence supporting the insight | ✅ | via `evidence_set_id` → `evidence/retrieve` |

### Assessment

A **limited** version of Public Pulse Moments is feasible now, using:
- `period-over-period` response's `changes` dict (volume delta)
- Any insights whose `period_start`/`period_end` overlap the detected change
- Evidence from those insights

A **robust** version requires:
- A new endpoint: `GET /api/v1/analytics/moments` — detecting statistically significant volume changes and linking them to topic/stance shifts within the same period
- Or: `start_date`/`end_date` filter support so topic/stance distributions can be compared across windows

**Recommendation:** Do NOT fabricate a Moments section. Implement a **simplified "Notable Periods" view** for Phase 12B showing the `period-over-period` change data and any linked insights. Document full Moments as a Phase 12D or Phase 13 enhancement.

---

## 12. AI Intelligence UX

### 12.1 Insight list view

- Sorted by `generated_at` descending (newest first)
- Status filter: All | Completed | Pending | Failed
- Program filter (uses global filter)
- Each insight card shows:
  - Insight type badge (e.g. "discourse_summary")
  - Program name + channel badge
  - `generated_at` timestamp
  - Generation status pill (color-coded)
  - Summary (first 2 lines, truncated)
  - Finding count
  - Verification status icon (✓ verified / ⏳ pending / ✗ failed / — not verified)

### 12.2 Insight detail layout

```
[Header bar: Type | Program | Period | LLM model | Generated at]
[Status banner: completed / running / failed]

[Summary section]
Lorem ipsum summary text from `insight.summary`

[Findings accordion]
  ▼ Finding 1 (confidence: HIGH)
    [finding text]
    [Evidence badges: ev-id-1, ev-id-2, ...]
    [Button: Explore Evidence →]
  ▶ Finding 2 (confidence: MEDIUM)
  ...

[Discourse Interpretation]
  discourse_interpretation text

[Limitations & Uncertainty]
  limitations | uncertainty_note

[Verification panel]
  ← See §14
```

### 12.3 Generating an insight (user flow)

1. User first retrieves evidence: Evidence Explorer → POST `/evidence/retrieve` → receive `evidence_set_id`
2. User navigates to "Generate Insight" → fills `evidence_set_id` + optional `program_id`
3. POST `/insights/generate` → `202 + job_id`
4. Job status card appears; polls `GET /jobs/{job_id}` every 3 seconds
5. On `completed`: show insight preview card with "View Insight" link
6. On `error`: show sanitized error message; offer "Retry"

---

## 13. Evidence Drill-Down UX

### 13.1 Evidence Explorer entry points

- From Insight detail: "Explore Evidence" button on each finding
- From navigation: standalone Evidence Explorer page
- From Program detail: "Retrieve Evidence" action

### 13.2 Evidence retrieval form (POST `/evidence/retrieve`)

```
┌──────────────────────────────────────────────────────┐
│ Evidence Explorer                                     │
│                                                       │
│ Topic:    [All Topics ▼]                             │
│ Stance:   [All ▼]                                    │
│ Program:  [All Programs ▼]                           │
│ Keywords: [tag input — space to add]                 │
│ Top K:    [20] (1–100)                               │
│                                                       │
│ [Retrieve Evidence]                                  │
└──────────────────────────────────────────────────────┘
```

Note: `start_date`/`end_date` are in the evidence schema and CAN be used here since the POST body (not route params) accepts them. This is one place where date filtering DOES work.

### 13.3 Evidence results panel

After POST → `EvidencePayloadOut`:

```
Evidence Set: [evidence_set_id]   Retrieved: [timestamp]   Method: [BM25]
Showing [N] of [total_matching_count] matching items

[Use this set for AI generation →]

┌─────────────────────────────────────────────────────────────────┐
│ Rank  │ Comment text           │ Program     │ Topic  │ Stance  │
│  1    │ [text_clean, trimmed]  │ Hiru Salk.  │ GOV    │ CRIT   │
│       │ relevance: 0.94        │ [video]     │ 95%    │ 88%    │
│ ...                                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 13.4 Drill-down chain

```
Evidence Item → Comment context panel (slide-in)
  Shows:
  - text_clean
  - posted_at
  - video_title
  - program_name → link to Program page
  - channel_name → link to Channel page
  - layer2_topic + confidence
  - layer4_stance + confidence
  - like_count
  - relevance_score
  - evidence_id (for reference, not editable)
  
  Does NOT show:
  - author_hash (excluded at schema level)
  - text_raw (excluded at schema level)
```

### 13.5 Provenance chain display

```
Insight [insight_id]
  └─ Finding [finding_id]: "[finding text]"
       └─ Evidence Set [evidence_set_id]
            └─ Evidence Item [evidence_id]
                 └─ Comment [text_clean]
                      └─ Video: [video_title]
                           └─ Program: [program_name]
                                └─ Channel: [channel_name]
```

This chain is always visible in the Evidence Explorer context panel. Every node links to its parent entity.

---

## 14. Faithfulness UX

### 14.1 Aggregate faithfulness panel (`GET /api/v1/analytics/faithfulness`)

```
┌─────────────────────────────────────────────────────┐
│ AI Faithfulness Overview                            │
│                                                     │
│ Grounding Score       ████████░░  [mean_grounding_  │
│                                    score × 100]%   │
│                                                     │
│ Claim Support Rate    ████████░░  [CSR]%            │
│ Contradiction Rate    ██░░░░░░░░  [CR]%             │
│                                                     │
│ Based on [N] verified insights                      │
│                                                     │
│ ⚠️ Metrics reflect AI-generated content only.      │
│    Unverified insights are not included.           │
└─────────────────────────────────────────────────────┘
```

⚠️ **Note:** `mean_partial_support_rate`, `mean_unsupported_claim_rate`, `mean_citation_precision` are missing from `FaithfulnessAnalyticsOut` — see §18 gap. These should be shown once resolved.

### 14.2 Verification report (`GET /api/v1/insights/{id}/verification`)

Full report view per insight:

**Score summary strip:**
```
Grounding    CSR       PSR       UCR       Contradiction   Citation
  [score]   [csr%]  [psr%]   [ucr%]       [cr%]          Precision
```

**Claim table:**
```
┌────────────┬──────────────────────────┬─────────────────┬─────────────────┐
│ Claim      │ Text                     │ Verdict         │ Reason          │
├────────────┼──────────────────────────┼─────────────────┼─────────────────┤
│ F1-C1      │ "The majority of..."    │ ✅ SUPPORTED    │ "Found in ev.." │
│ F1-C2      │ "Critics argue that..." │ ⚠️ PARTIAL     │ "Only 3 of 5…" │
│ F2-C1      │ "Economic concerns..."  │ ❌ UNSUPPORTED  │ "No evidence…" │
│ F3-C1      │ "Program X praised..." │ 🚫 CONTRADICTED │ "Evidence says" │
└────────────┴──────────────────────────┴─────────────────┴─────────────────┘
```

**Verdict badges:**
- `SUPPORTED` → green ✅
- `PARTIALLY_SUPPORTED` → amber ⚠️
- `UNSUPPORTED` → red ❌
- `CONTRADICTED` → dark red 🚫

**Plain-language explanation panel:**
> "What do these scores mean?"  
> Grounding Score measures overall faithfulness to the evidence. A score of 0.85 means 85% of the AI's claims were either fully or partially supported by the retrieved comments. Claims marked 'Contradicted' indicate the AI made a statement directly at odds with the evidence.

**Evidence links:** Each claim row expands to show `evidence_ids[]` — clickable to Evidence Explorer.

### 14.3 Verification trigger flow

- Button: "Verify Faithfulness" on insight detail (if not yet verified)
- POST `insights/{id}/verify` → 202 → job tracking (same poll pattern as generation)
- Polling every 3s until `completed` or `error`
- On complete: verification report panel appears inline in insight detail

---

## 15. Data Quality UX

### 15.1 From `GET /api/v1/analytics/data-quality`

Response has three fields:
- `overview: Dict` — raw dict (structure must be verified against repository)
- `average_confidence_by_layer: Dict[str, float]` — e.g. `{"layer2": 0.87, "layer4": 0.82}`
- `subissue_status: str` — always "ABSENT (permanently removed...)"

### 15.2 Page design

**Comment validity breakdown**
- From `OverviewKPIOut` (cross-referenced): `total_comments`, `valid_comments`, `noise_comments`, `pending_comments`
- Stacked bar: valid | noise | pending
- Noise rate prominently displayed with context
- Label: "Comments classified as NOISE by Layer 1 were not forwarded to topic or stance classification."

**Confidence by layer**
- `average_confidence_by_layer` — horizontal gauge bars
- layer2 confidence (Topic classifier)
- layer4 confidence (Stance classifier)
- No layer1 average shown (binary classifier — confidence less meaningful to display as average)

**Layer 3 / Sub-issue note:**
- Persistent info box: "Sub-issue classification (formerly Layer 3) was permanently removed from this research project. The `subissue_status` field confirms this: `[subissue_status value]`."
- This box should exist once, clearly, and never suggest Layer 3 might return.

**Processing status breakdown** (from `overview` dict, structure pending §18 verification):
- pending / scored / error / noise_exit — match `ProcessingStatusEnum` values
- Displayed as a table with counts

**Evidence & Insight coverage:**
- Total evidence sets created (from `overview` dict if available)
- Total insights generated (from `GET /api/v1/insights` count)
- Total verified insights (from `faithfulness.total_verifications`)

---

## 16. Collection Status Feasibility

### 16.1 What the database/API can provide

| Information | Available? | Source |
|---|---|---|
| Number of channels | ✅ | `overview.total_channels` |
| Number of programs | ✅ | `overview.total_programs` |
| Number of episodes | ✅ | `overview.total_videos` |
| Total comments collected | ✅ | `overview.total_comments` |
| Last scraped at (per video) | ✅ | `VideoOut.scraped_at` |
| Pipeline run history | ⚠️ | `pipeline_runs` table exists in ORM but NO API endpoint exposes it |
| Latest collection date | ⚠️ Partial | Can be inferred from `max(videos.scraped_at)` — NOT EXPOSED by API |
| Pipeline status (running/idle) | ❌ NOT SUPPORTED | No endpoint for `PipelineRun` records |
| Real-time scraping progress | ❌ NOT SUPPORTED | Pipeline runs from scripts, not API |
| Data freshness (last updated) | ❌ NOT SUPPORTED | Would need a dedicated endpoint |

### 16.2 What to implement

A limited **"Data Snapshot"** page showing:
- Count of channels, programs, episodes (from `overview`)
- Total comments collected (from `overview`)
- Most recently scraped episode date (from `GET /api/v1/analytics/episodes?limit=1` sorted by scraped_at desc — **requires sorting support**)

### 16.3 What NOT to fake

- Do NOT display a "Pipeline Status: Running / Idle" indicator — the API has no way to supply this
- Do NOT display "Last updated: [timestamp]" unless a dedicated endpoint is added
- Do NOT display a progress bar or collection percentage

### 16.4 Future enhancement required

Add `GET /api/v1/pipeline/status` endpoint returning: last pipeline run timestamp, run type, status, comments processed in last run. This requires exposing the `PipelineRun` ORM table via the API (additive, no schema change needed).

---

## 17. API → UI Mapping Table

| UI Feature | Endpoint | Key Params | Response Fields Used | Visualization | Loading State | Empty State | Error State |
|---|---|---|---|---|---|---|---|
| Global KPI cards | `GET /analytics/overview` | `channel_id`, `program_id`, `video_id` | All KPI fields | 4 metric cards | Skeleton cards | "No data for scope" | "Unable to load metrics" |
| Topic distribution chart | `GET /analytics/topics` | same | `distribution[]` | Horizontal bar | Bar shimmer | "No topic data" | Retry button |
| Stance donut | `GET /analytics/stances` | `topic_filter` + scope | `distribution[]` | Donut chart | Circle shimmer | "No stance data" | Retry button |
| Topic × Stance heatmap | `GET /analytics/topic-stance-matrix` | scope | `matrix` | 5×3 color grid | Grid shimmer | "No matrix data" | Retry button |
| Entity comparison | `GET /analytics/entity-matrix` | `entity_type`, `matrix_type` | `matrix` | Grouped bar | Bar shimmer | "No comparison data" | Retry button |
| Volume trend chart | `GET /analytics/volume-over-time` | `granularity` + scope | `data_points[]` | Area + line | Area shimmer | "No volume data" | Retry button |
| Period-over-period | `GET /analytics/period-over-period` | `period_days` + scope | `current_period`, `previous_period`, `changes` | Comparison table | Skeleton rows | "Insufficient data" | Retry button |
| Episode analytics table | `GET /analytics/episodes` | `limit`, `offset`, scope | `items[]`, `total` | Sortable table | Table skeleton | "No episodes found" | Retry button |
| Data quality page | `GET /analytics/data-quality` | scope | All fields | Bars + table | Multi-skeleton | "No quality data" | Retry button |
| Faithfulness overview | `GET /analytics/faithfulness` | `program_id` | All aggregate fields | Gauges + %s | Gauge shimmer | "No verifications yet" | Retry button |
| Channel list | `GET /channels` | — | `id, name, subscriber_count` | Cards | Card skeleton | "No channels" | Retry button |
| Program list | `GET /programs` | `channel_id`, `is_active` | All fields | Table | Table skeleton | "No programs" | Retry button |
| Program detail | `GET /programs/{id}` | — | All fields | Detail header | Header skeleton | "Not found" (404) | "Load error" |
| Program analytics | `GET /programs/{id}/analytics/*` | — | varies | per-section | per-section | per-section | per-section |
| Program videos | `GET /programs/{id}/videos` | `limit`, `offset` | All fields | Paginated list | List skeleton | "No episodes" | Retry button |
| Program insights | `GET /programs/{id}/insights` | `limit`, `offset` | All insight fields | Cards | Card skeleton | "No insights generated" | Retry button |
| Evidence retrieval | `POST /evidence/retrieve` | body params | `evidence_items[]`, `evidence_set_id` | Ranked table | Table skeleton | "No matching evidence" | Error banner |
| Insight list | `GET /insights` | `program_id`, `generation_status` | All insight fields | Cards | Card skeleton | "No insights" | Retry button |
| Insight detail | `GET /insights/{id}` | — | All insight fields + findings | Detail layout | Multi-skeleton | "Not found" | "Load error" |
| Generate insight | `POST /insights/generate` | body | `job_id` | 202 → job card | Spinner | — | Error banner |
| Verification report | `GET /insights/{id}/verification` | — | All report fields + claims | Report layout | Multi-skeleton | "Not verified yet" | Retry button |
| Verify insight | `POST /insights/{id}/verify` | — | `job_id` | 202 → job card | Spinner | — | Error banner |
| Job status polling | `GET /jobs/{job_id}` | — | `status`, `error`, `completed_at` | Status pill | Pulse animation | — | "Job not found" |
| Insight verification status | `GET /insights/{id}/verification` | — | grounding_score, CSR | Status badge on insight card | Badge skeleton | "Not verified" | — |

---

## 18. Missing API Capabilities

### Gap 1 — Date range filter not on route signatures (HIGH PRIORITY)

**Impact:** Cannot filter any analytics by date range (start_date / end_date) from the dashboard.  
**Root cause:** The service layer (`AnalyticsService`) accepts `start_date`/`end_date` but the route handler signatures in `analytics.py` and `programs.py` do not expose them as `Query()` parameters.  
**Fix required:** Add `start_date: Optional[datetime] = Query(None)` and `end_date: Optional[datetime] = Query(None)` to all analytics route handlers. **This is a Phase 12B prerequisite.**  
**Schema impact:** None — schemas already have `start_date`/`end_date` fields.  
**Test impact:** Phase 11 tests must not be regressed; new tests for date filter params must be added.

### Gap 2 — Volume granularity limited to daily/weekly/monthly

**Impact:** Cannot show hourly, quarterly, or yearly trends.  
**Fix (future):** Extend `pattern="^(hourly|daily|weekly|monthly|quarterly|yearly)$"` in route + service + repository.  
**Phase:** 12D or 13.

### Gap 3 — `FaithfulnessAnalyticsOut` missing fields

**Impact:** Cannot show `mean_partial_support_rate`, `mean_unsupported_claim_rate`, `mean_citation_precision` in the aggregate faithfulness view.  
**Fix:** Add these three fields to `FaithfulnessAnalyticsOut` schema and `get_faithfulness_analytics()` repository function.  
**Phase:** 12B prerequisite (or 12C acceptable if faithfulness page is deferred).

### Gap 4 — Topic-over-time endpoint missing

**Impact:** Cannot show how topic distribution has changed over time (time-series per topic, not just overall volume).  
**Fix (future):** New endpoint `GET /api/v1/analytics/topics-over-time` returning `{date: str, topic: str, count: int}[]`.  
**Phase:** 12D or 13.

### Gap 5 — `pipeline_runs` table not exposed via API

**Impact:** Cannot show collection status, last pipeline run, or data freshness.  
**Fix (future):** `GET /api/v1/pipeline/status` returning last run info.  
**Phase:** 12C or 13.

### Gap 6 — `DataQualityAnalyticsOut.overview` structure undocumented

**Impact:** The `overview: Dict` field is opaque — the frontend cannot safely map it without knowing the keys.  
**Fix:** Either convert to a typed Pydantic schema, or document the keys in the API spec. Frontend must handle this gracefully (unknown keys rendered as a generic key-value table).  
**Phase:** 12B prerequisite for robust Data Quality page.

### Gap 7 — Episode list not sorted by `scraped_at`

**Impact:** Cannot reliably show most recently collected episodes.  
**Fix:** Add `sort_by` parameter to `/analytics/episodes` endpoint.  
**Phase:** 12C.

### Gap 8 — No cross-scope topic trend endpoint

**Impact:** Public Pulse Moments (§11) cannot be fully implemented.  
**Fix:** Requires a `moments` or `topic-period-comparison` endpoint.  
**Phase:** 13.

---

## 19. Design System

### 19.1 Brand identity

**Name:** Public Pulse  
**Tagline:** "Understanding Sri Lankan public discourse"  
**Mark:** A waveform or pulse-signal icon in circular form — not government imagery, not a flag element. Suggests "listening to the public voice."

**Identity principle:** Civic intelligence product. Clean, serious, trustworthy. Not a startup product, not a government portal, not a university demo.

### 19.2 Color tokens

```css
/* Primary — Maroon (Sri Lankan civic reference, non-government) */
--color-primary-900: #4A0E0E;
--color-primary-700: #7B1C1C;
--color-primary-500: #9B2335;   /* Primary brand */
--color-primary-300: #C97C7C;
--color-primary-100: #F7E8E8;

/* Accent — Warm gold */
--color-accent-600: #B8860B;
--color-accent-400: #D4AC0D;    /* Accent / highlights */
--color-accent-100: #FDF6DC;

/* Surface */
--color-surface: #FAFAF9;
--color-surface-raised: #FFFFFF;
--color-surface-sunken: #F3F3F1;
--color-border: #E5E5E3;

/* Semantic */
--color-crit: #C0392B;          /* STANCE_CRIT */
--color-neut: #7F8C8D;          /* STANCE_NEUT */
--color-supp: #27AE60;          /* STANCE_SUPP */
--color-pending: #2980B9;
--color-noise: #BDC3C7;

/* Topics */
--color-topic-econ: #1A5276;
--color-topic-for:  #154360;
--color-topic-gov:  #7B241C;
--color-topic-law:  #1E8449;
--color-topic-media:#7D3C98;

/* Status */
--color-success: #1E8449;
--color-error: #C0392B;
--color-warning: #D35400;
--color-info: #2471A3;
```

### 19.3 Typography

```
Heading: "DM Sans" or "Plus Jakarta Sans" (Google Fonts — free, modern, readable)
Body: "Inter" (standard, legible)
Mono: "JetBrains Mono" (evidence text, IDs, code)
```

| Element | Size | Weight |
|---|---|---|
| H1 (page title) | 28px | 700 |
| H2 (section) | 22px | 600 |
| H3 (card title) | 18px | 600 |
| Body | 14px | 400 |
| Caption | 12px | 400 |
| KPI metric | 36px | 700 |
| KPI label | 12px | 500 (uppercase, tracked) |

### 19.4 Spacing

4px base unit. Common values: 4, 8, 12, 16, 24, 32, 48, 64px.

### 19.5 Border radius

- Cards: 12px
- Buttons: 8px
- Badges/pills: 999px (full round)
- Input fields: 8px
- Chart containers: 12px

### 19.6 Elevation / shadow

```css
--shadow-card: 0 1px 4px rgba(0,0,0,0.06), 0 2px 8px rgba(0,0,0,0.04);
--shadow-dropdown: 0 4px 16px rgba(0,0,0,0.12);
--shadow-modal: 0 8px 32px rgba(0,0,0,0.16);
```

No heavy drop shadows. Elevation is implied by background color shifts, not by large blurs.

### 19.7 Chart conventions

- All charts use the color tokens defined above
- All charts include: title, subtitle (scope indicator), legend (if > 1 series), axis labels
- No 3D effects
- No pie charts (use donuts — center text provides additional context)
- Color must be meaningful (topic always = topic color, stance always = stance color)
- Never use red for "bad" and green for "good" alone — always include text labels (accessibility)

### 19.8 Status indicators

| Status | Color | Icon |
|---|---|---|
| SUPPORTED | Green | ✅ |
| PARTIALLY_SUPPORTED | Amber | ⚠️ |
| UNSUPPORTED | Red | ❌ |
| CONTRADICTED | Dark red | 🚫 |
| completed | Green | ● |
| running | Blue pulse | ◌ |
| pending | Grey | ○ |
| error | Red | ✕ |

### 19.9 Motion / Animation

- Minimal animation. Duration: 150–250ms.
- Use `prefers-reduced-motion` media query to disable transitions.
- Chart render: fade in (opacity 0→1, 200ms).
- Skeleton shimmer: subtle horizontal sweep.
- No bounce, spring, or decorative motion.
- Tooltip: appear immediately on hover (no delay unless content is loading).

### 19.10 Dark/Light mode

**Decision: Light mode only for Phase 12B/12C.** Dark mode can be added in Phase 12D. Reason: the evidence text and faithfulness claim table require high contrast; designing for both modes doubles QA effort. System preference detection should be built in but the dark theme tokens are deferred.

### 19.11 Accessibility contrast

- All text on white/surface background: minimum 4.5:1 (WCAG AA)
- All text on colored backgrounds (badge, status pills): tested individually
- Primary brand maroon `#9B2335` on white: passes AA (tested: ~7.4:1)
- STANCE_CRIT `#C0392B` on white: passes AA

---

## 20. Chart Strategy

| Analytical Question | Chart Type | Rationale |
|---|---|---|
| KPI metric | Number card with label | Single value needs no chart |
| Topic distribution | Horizontal ranked bar | Shows proportion + ranking; labels readable |
| Stance distribution | Donut with center count | 3 values; center shows denominator |
| Volume over time | Area chart (total) + line (valid) | Area shows full picture; line shows signal |
| Period-over-period | Comparison table with Δ column | Precise numbers more useful than a chart for 2-period comparison |
| Topic × Stance matrix | Color-coded grid / heatmap | 5×3 = 15 cells; heatmap optimal |
| Entity comparison (matrix) | Grouped bar OR stacked bar | Grouped: absolute; Stacked: proportional — toggle |
| Episode analytics | Table with inline sparkline | Many rows; text data + mini visual |
| Confidence by layer | Horizontal gauge/progress bar | Single value per layer |
| Claim verification list | Table with verdict badges | Precise text + categorical label |
| Faithfulness scores | Gauge or circular progress | CSR/grounding feel like a percentage |

### Chart interaction spec

| Interaction | Behavior |
|---|---|
| Hover any chart | Tooltip appears at cursor; shows precise values |
| Tooltip content | Always includes: label, value, % if applicable, scope reminder |
| Click topic bar | Applies topic as global filter (if supported) |
| Click entity matrix cell | Navigates to entity detail page |
| Click episode row | Opens episode detail (video-scoped KPIs) |
| Legend click | Toggle series visibility (for grouped/stacked bars) |
| Empty chart state | Friendly message + icon; no broken axes |
| Loading chart state | Skeleton in the chart's shape (not a spinner in the center) |
| Error chart state | Error card with retry button |

---

## 21. State Management

### 21.1 State categories

| Category | What goes here | Tool |
|---|---|---|
| **Server state** | API responses, loading, error, stale | React Query (TanStack Query v5) |
| **Global filter state** | channelId, programId, videoId | Zustand (one small store) + URL sync |
| **URL state** | Filter params, page, tab | React Router v6 `useSearchParams` |
| **Local UI state** | Modal open/closed, accordion expanded, tab selected | `useState` inside components |

### 21.2 React Query usage

```typescript
// Example
const { data: overview, isLoading, error } = useQuery({
  queryKey: ['analytics', 'overview', { channelId, programId, videoId }],
  queryFn: () => api.getAnalyticsOverview({ channelId, programId, videoId }),
  staleTime: 5 * 60 * 1000,  // 5 min — analytics data doesn't change per-request
  gcTime: 10 * 60 * 1000,
});
```

- All filter-dependent queries include the filter in `queryKey` → auto-invalidated on filter change
- Job polling uses `refetchInterval` that stops when status is `completed` or `error`
- No manual cache invalidation needed for read-only analytics

### 21.3 Zustand filter store

```typescript
interface FilterStore {
  channelId: string | null;
  programId: string | null;
  videoId: string | null;
  setChannel: (id: string | null) => void;
  setProgram: (id: string | null) => void;
  setVideo: (id: string | null) => void;
  clearAll: () => void;
}
```

URL sync: `useFilterSync()` hook reads store → writes URL params; on mount reads URL params → writes store.

### 21.4 Avoid

- Redux (overkill for this application)
- Context API for frequently-changing state (causes unnecessary re-renders)
- `localStorage` for filter state (stale data risk)

---

## 22. Performance Architecture

### 22.1 Code splitting

- Each page/feature module is lazy-loaded: `React.lazy(() => import('./features/Overview'))`
- AI Intelligence pages (heaviest) load on-demand
- Recharts/Nivo loaded only when charts are visible

### 22.2 API call strategy

- No analytics computed client-side from raw data (enforced by API design)
- All aggregations are server-side — the frontend only renders what the API returns
- Evidence list (up to 100 items): render all in a virtualized list if N > 50 (`react-window`)
- Insight list: paginated (20 per page via `limit`/`offset`)
- Episode table: paginated (20 per page)

### 22.3 Caching

| Data | Strategy |
|---|---|
| Channel list | 30-min stale time (rarely changes) |
| Program list | 30-min stale time |
| Analytics overview | 5-min stale time |
| Volume chart | 5-min stale time |
| Insight detail | 2-min stale time (may be generating) |
| Job status | Real-time poll (3s) while pending/running, no cache when complete |

### 22.4 Filter debounce

- Keyword input in Evidence Explorer: 500ms debounce
- Date pickers (future): 300ms debounce
- Dropdown selections: immediate (no debounce — discrete change)

### 22.5 Image and asset optimization

- All icons: SVG inline (no network requests for icons)
- Logo: SVG
- No large image assets in the analytics dashboard

---

## 23. Security & Privacy Architecture

### 23.1 API key handling

```
Frontend reads: VITE_API_KEY (build-time env variable)
Sent as: X-API-Key header on every request

CRITICAL: VITE_ prefix variables are bundled into the JS build.
They are visible to anyone who views page source.
```

**Implication:** If the API key must remain secret, the frontend cannot hold it. Two options:
1. **Public-read API** — set no `API_KEY` env var on the server → `verify_api_key` passes all requests. Use for read-only analytics (acceptable if the data is not sensitive).
2. **Backend-for-Frontend (BFF) proxy** — the frontend calls a thin proxy on the same domain that injects the API key server-side. The browser never sees the key.

**Recommendation for Phase 12B:** Option 1 (no key enforcement) for the analytics read endpoints. Keep `API_KEY` enforcement on the write endpoints (`/insights/generate`, `/evidence/retrieve`, `/insights/verify`) if write access must be restricted.

### 23.2 Privacy enforcement at the frontend layer

Even though the API enforces privacy, the frontend adds an additional contract:

- `author_hash` — no field exists in any API schema, but if it ever appeared: **never render it**
- `text_raw` — not in any schema; never display
- `text_clean` — only rendered in the Evidence Explorer panel (where it is analytically necessary) — never shown in aggregate lists or KPI views
- No free-text search that could be used to find specific individuals

### 23.3 CORS

The backend reads `DASHBOARD_ORIGIN` env var (`api/main.py` L42). Set this to the deployed frontend origin:
```
DASHBOARD_ORIGIN=https://public-pulse-dashboard.example.com
```
During development: `http://localhost:5173` (Vite default).

### 23.4 Environment variables

```
# .env.local (dashboard/) — never committed
VITE_API_BASE_URL=http://localhost:8000
VITE_API_KEY=                # Leave empty for local dev if API_KEY not set on server
```

`.env.local` must be in `.gitignore`. The `dashboard/.gitignore` must include:
```
.env.local
.env.*.local
dist/
node_modules/
```

### 23.5 Error sanitization

Backend already returns structured error responses. Frontend must NOT display raw Python exception tracebacks. Map HTTP status codes to user-friendly messages:
- 401 → "Authentication required. Please check your access configuration."
- 404 → "Not found. The requested resource does not exist."
- 422 → "Invalid request. Please check the filter values."
- 500 → "Server error. Please try again in a moment."

Never display `exc.detail` from 500 responses directly.

---

## 24. Accessibility

### 24.1 Keyboard navigation

- All interactive elements are keyboard-reachable via Tab
- Focus order follows visual reading order
- Custom components (dropdowns, modals, accordions) implement ARIA patterns:
  - Dropdown: `role="combobox"` + `role="listbox"` + arrow key navigation
  - Modal: `role="dialog"` + focus trap + Escape closes
  - Accordion: `role="button"` + `aria-expanded`

### 24.2 Focus states

- Visible focus ring on all interactive elements: `outline: 2px solid var(--color-primary-500); outline-offset: 2px;`
- Never `outline: none` without an alternative
- Focus ring passes 3:1 contrast against background

### 24.3 Chart accessibility

- All charts have an `aria-label` describing the content: `aria-label="Topic distribution: Governance 34%, Economics 28%, ..."`
- Provide a "View as table" toggle for all charts (shows the underlying data in a `<table>`) for screen reader users
- Color is never the only encoding — always supplement with text labels or patterns

### 24.4 Semantic HTML

- Page landmarks: `<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>`
- Headings in correct hierarchy (H1 per page, H2 per section)
- Status messages use `role="status"` or `role="alert"` as appropriate
- Evidence table uses `<table>` with `<th scope="col">` headers

### 24.5 Reduced motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 24.6 Language and direction

- `<html lang="en">` on the document
- Evidence text may contain Sinhala script — the system font stack must include a Sinhala-capable font or the browser default will handle it. Do not override with a Latin-only web font on text that may contain Sinhala.

---

## 25. Testing Strategy

### 25.1 Component tests (Vitest + React Testing Library)

- All shared components: `FilterBar`, `KPICard`, `TopicBar`, `StanceDonut`, `MatrixHeatmap`, `EvidenceTable`, `InsightCard`, `VerificationReport`
- Test render, loading state, empty state, error state, and user interactions
- Mock API using `msw` (Mock Service Worker) — type-safe mocks from OpenAPI schema

### 25.2 API integration tests

- One test per API endpoint the frontend uses
- Test: correct params sent, correct response parsed, correct UI rendered
- Uses `msw` handlers against the real OpenAPI response shapes

### 25.3 Filter tests

- Global filter changes propagate to all chart queries
- URL params are correctly serialized / deserialized
- Cascade: selecting program → channel pre-fills
- Clear all → all queries revert to global scope

### 25.4 Privacy contract tests

- **Test: `author_hash` never appears in DOM.** After any API response, scan rendered HTML for "author_hash" — must not be found.
- **Test: `text_raw` never appears in DOM.** Same check.
- **Test: `text_clean` only appears in Evidence Explorer context.** Assert it is not rendered on Overview, Topics, Stance, or any aggregate page.

### 25.5 Layer 3 contract test (frontend mirror)

- Scan all rendered component output for the string "layer3" (case-insensitive) — must not appear.
- This mirrors the existing backend taxonomy contract test.

### 25.6 Accessibility tests

- `jest-axe` run on all major page layouts
- Keyboard navigation flow test for: filter bar → chart → drill-down → evidence panel
- Color contrast verified by design-time token definitions (not runtime test)

### 25.7 Responsive tests

- Playwright (or Vitest browser mode) at breakpoints: 375px (mobile), 768px (tablet), 1280px (desktop), 1920px (wide)
- Critical: Overview, Topic × Stance matrix, Episode table

### 25.8 Critical user journeys (E2E)

- Journey 1: Land on Overview → change program filter → see charts update → period-over-period update
- Journey 2: Navigate to Evidence Explorer → retrieve evidence → navigate to Generate Insight → poll until complete → view Insight detail
- Journey 3: On Insight detail → trigger verification → poll until complete → view Faithfulness report → expand a CONTRADICTED claim
- Journey 4: Navigate Channels → select channel → view Programs → select program → view program analytics suite

### 25.9 Test files to create

```
dashboard/src/
├── components/__tests__/
│   ├── KPICard.test.tsx
│   ├── TopicDistributionChart.test.tsx
│   ├── StanceDonut.test.tsx
│   ├── MatrixHeatmap.test.tsx
│   ├── EvidenceTable.test.tsx
│   ├── InsightCard.test.tsx
│   ├── VerificationReport.test.tsx
│   └── FilterBar.test.tsx
├── features/__tests__/
│   ├── overview.test.tsx
│   ├── evidence-explorer.test.tsx
│   ├── insight-generation-flow.test.tsx
│   └── verification-flow.test.tsx
├── hooks/__tests__/
│   ├── useFilterState.test.ts
│   ├── useJobPoll.test.ts
│   └── useFilterSync.test.ts
└── __tests__/
    ├── privacy-contracts.test.tsx
    ├── layer3-contracts.test.tsx
    └── accessibility.test.tsx
```

---

## 26. Deployment Architecture

### 26.1 Current deployment signals

- `Dockerfile` exposes port 7860 → **Hugging Face Spaces** target (confirmed by `deployment/huggingface/README.md`: "sdk: docker, app_port: 7860")
- `deployment/docker/Dockerfile.api` — Docker API image
- `pyproject.toml` has `streamlit>=1.35` — originally intended for Streamlit on HF Spaces

### 26.2 Recommended production architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Hugging Face Spaces (Docker)                                           │
│                                                                         │
│  ┌──────────────────────┐      ┌──────────────────────────────────────┐│
│  │  React + Vite        │      │  FastAPI (uvicorn)                   ││
│  │  (Static build       │ ←──► │  api/main.py                        ││
│  │   served by nginx    │      │  /api/v1/*                          ││
│  │   or by FastAPI      │      │                                      ││
│  │   static mount)      │      │  Background tasks (insight gen /     ││
│  └──────────────────────┘      │  verification) run in-process       ││
│                                └──────────────────────────────────────┘│
│                                         │                               │
│                                         ▼                               │
│                               PostgreSQL (external)                     │
│                               (HF Spaces → Supabase or Neon free tier) │
└─────────────────────────────────────────────────────────────────────────┘
```

### 26.3 Deployment options evaluated

| Option | Fit | Notes |
|---|---|---|
| HF Spaces Docker | ✅ Best fit | Existing Dockerfile; port 7860; free for open source |
| Separate frontend on Vercel/Netlify | ✅ Good | Static Vite build; no backend needed on frontend host |
| Monorepo Docker (nginx + uvicorn) | ✅ Clean | nginx serves Vite build + proxies `/api/v1` to uvicorn |
| Railway / Render | ✅ Good | Easy PostgreSQL + FastAPI pairing |
| Streamlit Cloud | ❌ Not suitable | Requires Python Streamlit; incompatible with React decision |

### 26.4 Recommended Phase 12 deployment

**Option A (simplest, HF Spaces):** FastAPI serves the Vite static build at `/` via `StaticFiles` mount, and serves the API at `/api/v1`. Single Docker container.

**Option B (best separation):** Two services — FastAPI backend on HF Spaces / Railway, Vite frontend on Netlify/Vercel. CORS configured between them. Database: Supabase or Neon (free PostgreSQL).

**Recommend Option A for Phase 12B/12C, Option B for production.**

---

## 27. Proposed Frontend Folder Structure

```
dashboard/
├── package.json
├── package-lock.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── index.html
├── .env.local                    # gitignored
├── .env.example
├── .gitignore
├── public/
│   ├── favicon.svg
│   └── og-image.png
└── src/
    ├── main.tsx                  # React root
    ├── App.tsx                   # Router setup
    ├── api/
    │   ├── client.ts             # axios/fetch wrapper with base URL + API key header
    │   ├── analytics.ts          # API functions: getOverview(), getTopics(), etc.
    │   ├── catalog.ts            # getChannels(), getPrograms(), getVideos()
    │   ├── evidence.ts           # retrieveEvidence()
    │   ├── insights.ts           # generateInsight(), getInsight(), listInsights()
    │   ├── verification.ts       # verifyInsight(), getVerificationReport()
    │   ├── jobs.ts               # getJobStatus()
    │   └── types.ts              # TypeScript types (generated from OpenAPI or manual)
    ├── components/
    │   ├── ui/                   # Primitive components
    │   │   ├── Card.tsx
    │   │   ├── Badge.tsx
    │   │   ├── Button.tsx
    │   │   ├── Skeleton.tsx
    │   │   ├── Tooltip.tsx
    │   │   ├── Modal.tsx
    │   │   └── StatusPill.tsx
    │   ├── charts/               # Chart wrappers
    │   │   ├── TopicBarChart.tsx
    │   │   ├── StanceDonut.tsx
    │   │   ├── VolumeAreaChart.tsx
    │   │   ├── MatrixHeatmap.tsx
    │   │   ├── EntityGroupedBar.tsx
    │   │   └── FaithfulnessGauge.tsx
    │   ├── filters/              # Filter components
    │   │   ├── GlobalFilterBar.tsx
    │   │   ├── ChannelSelect.tsx
    │   │   ├── ProgramSelect.tsx
    │   │   ├── TopicSelect.tsx
    │   │   └── GranularityToggle.tsx
    │   ├── layout/               # Layout components
    │   │   ├── Sidebar.tsx
    │   │   ├── TopBar.tsx
    │   │   ├── PageHeader.tsx
    │   │   ├── ScopeIndicator.tsx
    │   │   └── EmptyState.tsx
    │   └── shared/               # Cross-feature
    │       ├── KPICard.tsx
    │       ├── InsightCard.tsx
    │       ├── EvidenceTable.tsx
    │       ├── FindingAccordion.tsx
    │       ├── VerificationReport.tsx
    │       └── JobStatusCard.tsx
    ├── features/
    │   ├── overview/
    │   │   └── OverviewPage.tsx
    │   ├── explore/
    │   │   ├── VolumePage.tsx
    │   │   ├── TopicsPage.tsx
    │   │   ├── StancePage.tsx
    │   │   └── TopicStancePage.tsx
    │   ├── sources/
    │   │   ├── ChannelsPage.tsx
    │   │   ├── ChannelDetailPage.tsx
    │   │   ├── ProgramsPage.tsx
    │   │   ├── ProgramDetailPage.tsx
    │   │   └── EpisodesPage.tsx
    │   ├── ai/
    │   │   ├── InsightsPage.tsx
    │   │   ├── InsightDetailPage.tsx
    │   │   ├── EvidenceExplorerPage.tsx
    │   │   └── FaithfulnessPage.tsx
    │   └── data/
    │       ├── DataQualityPage.tsx
    │       ├── CollectionStatusPage.tsx
    │       └── MethodologyPage.tsx
    ├── hooks/
    │   ├── useFilterState.ts     # Zustand store accessor
    │   ├── useFilterSync.ts      # URL ↔ store sync
    │   ├── useJobPoll.ts         # Poll /jobs/{id} until terminal state
    │   ├── useAnalytics.ts       # Composed hook for analytics queries
    │   └── usePagination.ts
    ├── store/
    │   └── filterStore.ts        # Zustand store definition
    ├── lib/
    │   ├── constants.ts          # TOPIC_LABELS, STANCE_LABELS, TOPIC_COLORS
    │   ├── formatters.ts         # formatNumber, formatPercent, formatDate
    │   └── queryClient.ts        # React Query client config
    ├── styles/
    │   ├── tokens.css            # CSS custom properties (color, spacing, radius)
    │   └── global.css
    └── __tests__/
        ├── privacy-contracts.test.tsx
        └── layer3-contracts.test.tsx
```

---

## 28. Dependency Recommendations

### 28.1 Core

| Package | Version | Purpose |
|---|---|---|
| `react` | 18.x | UI framework |
| `react-dom` | 18.x | DOM rendering |
| `react-router-dom` | 6.x | Routing + URL state |
| `typescript` | 5.x | Type safety |
| `vite` | 5.x | Build tool + HMR |
| `@vitejs/plugin-react` | latest | Vite React plugin |

### 28.2 Data fetching & state

| Package | Version | Purpose |
|---|---|---|
| `@tanstack/react-query` | 5.x | Server state, caching, polling |
| `zustand` | 4.x | Global filter store (tiny, no boilerplate) |
| `axios` | 1.x | HTTP client (typed interceptors for API key header) |

### 28.3 Charts

| Package | Version | Purpose |
|---|---|---|
| `recharts` | 2.x | Area, bar, donut charts — React-native, no D3 knowledge required |

Alternative: `@nivo/core` + individual `@nivo/*` packages if more chart types are needed. Recharts is sufficient for Phase 12B/12C.

### 28.4 UI utilities

| Package | Version | Purpose |
|---|---|---|
| `tailwindcss` | 3.x | Utility CSS (optional but strongly recommended for rapid UI development) |
| `clsx` | 2.x | Conditional class names |
| `react-window` | 1.x | Virtualized list for Evidence Explorer (100 items) |
| `date-fns` | 3.x | Date formatting (lightweight, tree-shakeable) |

### 28.5 Testing

| Package | Version | Purpose |
|---|---|---|
| `vitest` | 1.x | Test runner |
| `@testing-library/react` | 14.x | Component testing |
| `@testing-library/user-event` | 14.x | User interaction simulation |
| `msw` | 2.x | API mocking |
| `jest-axe` | 8.x | Accessibility checks |
| `playwright` | 1.x | E2E critical journeys |

### 28.6 What NOT to add

- **Redux / Redux Toolkit** — overkill for this application
- **MUI / Ant Design / Chakra** — heavy; use Tailwind + custom components for brand control
- **Next.js** — SSR not needed; the dashboard is a client-side analytics SPA
- **D3.js** directly — Recharts wraps D3 sufficiently
- **GraphQL client** — the API is REST

---

## 29. Implementation Phases — 12B / 12C / 12D

### Phase 12B — Foundation + Core Analytics (Priority 1)

**Prerequisites before writing any React:**
1. ✅ Resolve §18 Gap 1: Add `start_date`/`end_date` to all analytics route signatures
2. ✅ Resolve §18 Gap 3: Add missing fields to `FaithfulnessAnalyticsOut`
3. ✅ Resolve §18 Gap 6: Document/type `DataQualityAnalyticsOut.overview` keys

**Then implement:**
- Vite project bootstrap
- Design system (tokens, typography, base components)
- Global filter bar (channel, program, video selectors)
- URL ↔ filter state sync
- Overview page (all KPIs, topic chart, stance donut, T×S matrix, P-o-P)
- Explore — Volume & Trends
- Explore — Topics
- Explore — Stance
- Explore — Topic × Stance
- Sources — Programs page + detail
- All tests for above features

**Deliverable:** All 276 existing backend tests still passing. 40+ new Phase 12B frontend tests.

### Phase 12C — Sources + Data + AI Insights Foundation

- Sources — Channels + Channel detail
- Sources — Episodes table
- AI Insights list + detail (view only, no generation form initially)
- Evidence Explorer (POST + results table)
- Data Quality page
- Collection Status (limited, per §16)
- Methodology static page
- Performance optimizations (lazy loading, virtualization)

### Phase 12D — AI Generation + Faithfulness + Polish

- Insight generation flow (Evidence → Generate → Poll → View)
- Faithfulness verification flow (Trigger → Poll → Report)
- Faithfulness aggregate analytics page
- Public Pulse Moments (simplified "Notable Periods" view)
- Dark mode tokens (optional)
- Hourly/quarterly granularity (if §18 Gap 2 resolved by this phase)
- E2E Playwright tests for all critical journeys
- Deployment configuration (Docker or Vercel)

---

## 30. Risks and Mitigations

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| §18 Gap 1 (date filter) introduces regression in Phase 11 tests | HIGH | Medium | Add `start_date`/`end_date` params as `Optional` with `None` default — existing tests pass unchanged |
| Sarcasm view (`sarcasm_view.py`) is carried forward | HIGH | Low | Explicitly delete or do not import; Layer 3 contract test already blocks this at backend |
| `program_type: null` causes confusing UI | Medium | High | Filter it out of all displays; document as "not yet classified" in Methodology |
| Background tasks fail silently (no reliable push) | Medium | Medium | Job polling every 3s with timeout (e.g. after 5 min, mark as "taking longer than expected") |
| Evidence `text_clean` exposed in wrong context | HIGH | Low | Component-level tests assert text_clean is absent from non-Evidence pages |
| `DataQualityAnalyticsOut.overview` dict has unknown structure | Medium | High | Render as generic key-value table; file §18 Gap 6 to type it before Data Quality page ships |
| HF Spaces SQLite vs PostgreSQL mismatch | HIGH | Medium | Enforce `DATABASE_URL` env var on deploy; never use SQLite in production |
| Pydantic v2 `Config` class deprecation warning | Low | Certain | Known Phase 11 debt; fix in Phase 12B when touching schemas |
| CORS misconfiguration on deploy | HIGH | Medium | Set `DASHBOARD_ORIGIN` exactly to deployed frontend origin; test OPTIONS preflight |
| Lang script rendering (Sinhala in evidence) | Low | Certain | System font fallback handles it; do not override with Latin-only font on `text_clean` fields |

---

## 31. Files That Would Be Created/Modified

### New files (frontend — Phase 12B+)

All files under `dashboard/` (React workspace). Python backend files in `dashboard/` are superseded. See §27 for full structure.

### Backend files that must be modified (Phase 12B prerequisite — additive only)

| File | Change |
|---|---|
| `api/routes/analytics.py` | Add `start_date`, `end_date` Query params to all route handlers |
| `api/routes/programs.py` | Same addition for all analytics sub-routes |
| `api/schemas/analytics.py` | Add `mean_partial_support_rate`, `mean_unsupported_claim_rate`, `mean_citation_precision` to `FaithfulnessAnalyticsOut`; type the `overview` dict in `DataQualityAnalyticsOut` |
| `src/public_pulse/database/repository.py` | Extend `get_faithfulness_analytics()` to return the three new metrics |
| `tests/test_api_analytics.py` | Add tests for new date filter params (additive) |

### Files that must NOT be carried forward

| File | Reason |
|---|---|
| `dashboard/components/sarcasm_view.py` | References superseded taxonomy; sarcasm merged into STANCE_CRIT |
| `dashboard/components/sentiment_tracker.py` | Empty Streamlit stub |
| `dashboard/components/topic_meter.py` | Empty Streamlit stub |
| `dashboard/components/program_compare.py` | Empty Streamlit stub |
| `dashboard/app.py` | Streamlit stub; superseded by React app |

These files should be removed in Phase 12B (after confirming no test imports them).

---

## 32. Final Go/No-Go Recommendation

### ✅ GO — with pre-implementation prerequisites

**The Phase 12 dashboard is ready to implement**, subject to the following conditions being satisfied before Phase 12B coding begins:

| # | Condition | Severity |
|---|---|---|
| 1 | §18 Gap 1 resolved (date filter on route signatures) | MUST |
| 2 | §18 Gap 3 resolved (faithfulness schema extended) | SHOULD |
| 3 | §18 Gap 6 resolved (data quality overview typed) | SHOULD |
| 4 | Confirmation that 276/276 tests still pass after backend prerequisites | MUST |
| 5 | `dashboard/components/sarcasm_view.py` and other stubs removed | SHOULD |

**The API is analytically sufficient** to build a high-value civic intelligence dashboard. The evidence system, insight system, faithfulness system, and analytics aggregation system are all production-grade.

**The maximum-analysis principle is met:** every analytics endpoint performs server-side aggregation. The frontend will never download raw comments.

**Privacy is enforced at the schema level:** `author_hash` and `text_raw` are not present in any response schema. Frontend contracts can mirror this at the component test level.

**The recommended technology stack** (React + Vite + React Query + Zustand + Recharts) is appropriate, widely used in production analytics products, and fully compatible with the HF Spaces Docker deployment target.

---

*End of Phase 12A Audit*  
*Next step: User review and approval → Phase 12B implementation begins*
