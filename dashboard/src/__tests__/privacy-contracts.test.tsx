/**
 * Privacy contract tests.
 *
 * These tests verify that privacy-violating fields NEVER appear in
 * any rendered component output. They act as a regression guard —
 * if a developer accidentally exposes text_raw, author_hash, or PII,
 * these tests will catch it immediately.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

/* ─── EvidenceTable privacy test ─────────────────────────── */
import { EvidenceTable } from '../components/shared/EvidenceTable';
import type { EvidenceItemOut } from '../types/api';

const MOCK_EVIDENCE: EvidenceItemOut[] = [
  {
    rank: 1,
    evidence_id: 'e001',
    comment_id: 'c001',
    text_clean: 'The government should be held accountable for rising prices.',
    relevance_score: 0.92,
    layer2_topic: 'economic_governance',
    layer2_confidence: 0.91,
    layer4_stance: 'CRITICAL',
    layer4_confidence: 0.88,
    video_id: 'v001',
    video_title: 'News Hour Episode 1',
    channel_name: 'Sirasa TV',
    program_name: 'News Hour',
    like_count: 5,
  },
];

describe('EvidenceTable — privacy contracts', () => {
  it('does NOT render author_hash in evidence table', () => {
    render(<EvidenceTable items={MOCK_EVIDENCE} />);
    expect(screen.queryByText(/author_hash/i)).toBeNull();
    expect(screen.queryByText(/[0-9a-f]{40,}/i)).toBeNull();
  });

  it('does NOT render text_raw field label', () => {
    render(<EvidenceTable items={MOCK_EVIDENCE} />);
    expect(screen.queryByText(/text_raw/i)).toBeNull();
  });

  it('does NOT render "username" as a field label', () => {
    render(<EvidenceTable items={MOCK_EVIDENCE} />);
    expect(screen.queryByText(/^username$/i)).toBeNull();
  });

  it('DOES render text_clean content', () => {
    render(<EvidenceTable items={MOCK_EVIDENCE} />);
    expect(screen.getByText(/government should be held accountable/i)).toBeTruthy();
  });

  it('DOES render channel and program provenance', () => {
    render(<EvidenceTable items={MOCK_EVIDENCE} />);
    expect(screen.getByText(/Sirasa TV/i)).toBeTruthy();
    expect(screen.getByText(/News Hour/i)).toBeTruthy();
  });
});

/* ─── InsightCard privacy test ───────────────────────────── */
import { InsightCard } from '../components/shared/InsightCard';
import type { InsightOut } from '../types/api';

const MOCK_INSIGHT: InsightOut = {
  insight_id: 'i001',
  program_id: 'p001',
  query: 'economic policy',
  summary: 'Public discourse shows increasing concern about economic governance.',
  findings: [],
  discourse_interpretation: '',
  limitations: '',
  insight_type: 'discourse',
  generation_status: 'completed',
  evidence_count_used: 15,
  llm_provider: 'google',
  llm_model: 'gemini-1.5-flash',
  prompt_version: 'v1',
  generated_at: '2024-01-15T10:00:00Z',
};

describe('InsightCard — privacy contracts', () => {
  it('does NOT expose author_hash', () => {
    render(<InsightCard insight={MOCK_INSIGHT} />);
    expect(screen.queryByText(/author_hash/i)).toBeNull();
  });

  it('does NOT expose text_raw', () => {
    render(<InsightCard insight={MOCK_INSIGHT} />);
    expect(screen.queryByText(/text_raw/i)).toBeNull();
  });

  it('DOES render insight summary', () => {
    render(<InsightCard insight={MOCK_INSIGHT} />);
    expect(screen.getByText(/increasing concern about economic governance/i)).toBeTruthy();
  });
});
