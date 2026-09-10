# Phase 8 — Evidence Extraction & Retrieval Documentation

This document describes the design, architecture, retrieval workflow, deterministic ranking, evidence reproducibility, and research evaluation boundaries for Phase 8 in Public Pulse.

---

## 1. Overview & Conceptual Architecture

Phase 8 implements the evidence retrieval layer that extracts traceable, representative, high-quality YouTube comment evidence from database records classified during Phase 7.

### Core Conceptual Distinction

```
[Retrieval Query]
       │
       ▼
[Evidence Set] ── (persisted with unique evidence_set_id & query_params JSON)
       │
       ├──► [Evidence Items] (ordered, individual scored comments)
       │
       ▼
[Phase 9 Grounded LLM] (Receives EvidencePayload ONLY; no direct SQL access)
       │
       ▼
    [Insight] ── (references evidence_set_id)
```

> [!IMPORTANT]
> **Strict Architectural Rules:**
> - **Evidence retrieval is 100% independent of Insight generation.** An `EvidenceSet` is produced by a `RetrievalQuery` before any `Insight` exists.
> - **Layer 3 does NOT exist** anywhere in retrieval logic or data models.
> - **Dense embeddings / vector databases are NOT introduced** in Phase 8.
> - **Phase 9 LLM is NOT implemented** in Phase 8.

---

## 2. 10-Stage Retrieval Pipeline

```
[1. Classified Comments in Database] (processing_status = 'scored')
                 │
                 ▼
[2. Eligibility & Quality Filtering] (Exclude NOISE, enforce text length & min confidence)
                 │
                 ▼
[3. Metadata + Topic/Stance Constraints] (Filter by Program, Channel, Date Range, Topic, Stance)
                 │
                 ▼
[4. Candidate Retrieval Pool] (Fetch matching SQL candidate records)
                 │
                 ▼
[5. Relevance Ranking] (Compute BM25 score over text_clean / text_raw)
                 │
                 ▼
[6. Deterministic Sorting & Tie-Breaking] (Sort by relevance_score, posted_at, like_count, comment_id)
                 │
                 ▼
[7. Duplicate Control] (Remove exact & near-duplicate comment texts)
                 │
                 ▼
[8. Diversity & Contradiction Preservation] (Apply per-video cap & multi-stance proportional quota)
                 │
                 ▼
[9. Top-K Evidence Set Selection] (Extract top-K items)
                 │
                 ▼
[10. Persist Evidence Provenance] (Insert evidence_sets & evidence records with evidence_set_id)
```

---

## 3. Deterministic Multi-Key Sorting

To guarantee 100% reproducible evidence set ordering across repeated executions over identical data, Phase 8 sorting uses an explicit 4-tuple:

$$\text{Sort Order} = \big( \text{relevance\_score} \downarrow, \; \text{posted\_at} \downarrow, \; \text{like\_count} \downarrow, \; \text{comment\_id} \uparrow \big)$$

1. **`relevance_score` DESC**: BM25 relevance score (rounded to 6 decimal places).
2. **`posted_at` DESC**: Latest comment timestamp.
3. **`like_count` DESC**: Comment engagement level.
4. **`comment_id` ASC**: UUID string lexicographical comparison (guaranteed absolute tie-breaker).

---

## 4. Multi-Stance Proportional Preservation

When `stance = 'ALL'` is requested for a topic query, the Evidence Set allocates top-$K$ slots proportionally across stances based on their natural distribution in the candidate pool:

$$\text{Quota}(\text{stance}_s) = \left\lceil K \times \frac{N(\text{topic}, \text{stance}_s)}{N(\text{topic})} \right\rceil$$

This preserves contradictory opinions, reflects genuine public sentiment balance, and prevents bias toward a single political narrative.

---

## 5. Duplicate Control & Ethical Safeguards

- **Text-Based Deduplication**: Exact duplicate strings and near-duplicate copypasta (Jaccard similarity $\ge 0.85$) are filtered out using text content only.
- **Zero Author Profiling**: `author_hash` is an anonymized SHA-256 string. Author identity is **NEVER** used for grouping, profiling, ranking, or user analysis.
- **No Political Targeting**: The system does NOT create voter profiles, individual political scores, or targeted recommendations.

---

## 6. Phase 8 $\rightarrow$ Phase 9 Data Contract (`EvidencePayload`)

Phase 8 delivers a typed `EvidencePayload` structure to Phase 9:

```json
{
  "evidence_set_id": "9b1e4c2a-8f3d-4e12-b501-7a8c9d0e1f2a",
  "retrieved_at": "2026-09-08T15:45:00Z",
  "retrieval_metadata": {
    "topic": "TOPIC_ECON_SERV",
    "stance": "ALL",
    "program_id": "4a2f8b01-...",
    "top_k": 20,
    "confidence_thresholds": {"layer1": 0.5, "layer2": 0.7, "layer4": 0.7},
    "retrieval_method": "hybrid_bm25_v1"
  },
  "evidence_count": 10,
  "total_matching_count": 342,
  "retrieval_method": "hybrid_bm25_v1",
  "evidence_items": [
    {
      "rank": 1,
      "evidence_id": "11111111-...",
      "comment_id": "22222222-...",
      "text_raw": "ආර්ථික ප්‍රශ්න විසඳන්න වැඩපිළිවෙලක් නෑ...",
      "text_clean": "ආර්ථික ප්‍රශ්න විසඳන්න වැඩපිළිවෙලක් නෑ...",
      "posted_at": "2026-02-15T14:30:00Z",
      "video_id": "33333333-...",
      "video_title": "Salakuna 2026-02-15 Episode",
      "program_name": "Hiru Salakuna",
      "channel_name": "Hiru News",
      "layer2_topic": "TOPIC_ECON_SERV",
      "layer2_confidence": 0.94,
      "layer4_stance": "STANCE_CRIT",
      "layer4_confidence": 0.91,
      "like_count": 42,
      "relevance_score": 0.884210
    }
  ]
}
```

---

## 7. Research Evaluation & Limitations

1. **BM25 Baseline**: BM25 serves as an initial lexical baseline. Evaluation of Sinhala inflection, Singlish spelling variation, and lexical mismatch remains an open research topic for evaluation against human relevance judgments.
2. **Confidence Thresholds**: Default thresholds (Layer 1 $\ge 0.50$, Layer 2 $\ge 0.70$, Layer 4 $\ge 0.70$) are configurable quality heuristics, not scientifically proven absolute truths.
3. **Population Scope Disclaimer**: Analyzed YouTube comments represent online video audience discourse only and do **NOT** represent the overall public opinion of the entire Sri Lankan population.
