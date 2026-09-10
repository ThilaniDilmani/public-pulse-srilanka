import React, { useState } from 'react';
import { PageHeader } from '../../components/layout/PageHeader';
import { ScopeIndicator } from '../../components/layout/ScopeIndicator';
import { GlobalFilterBar } from '../../components/filters/GlobalFilterBar';
import { EvidenceTable } from '../../components/shared/EvidenceTable';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { useFilterStore } from '../../store/filterStore';
import { api } from '../../api/client';
import type { EvidencePayloadOut } from '../../types/api';
import { useNavigate } from 'react-router-dom';
import { Search, Lightbulb, AlertCircle } from 'lucide-react';

export const EvidenceExplorerPage: React.FC = () => {
  const navigate = useNavigate();
  const { programId, channelId } = useFilterStore();

  const [query, setQuery]       = useState('');
  const [topK, setTopK]         = useState(10);
  const [loading, setLoading]   = useState(false);
  const [generating, setGen]    = useState(false);
  const [payload, setPayload]   = useState<EvidencePayloadOut | null>(null);
  const [error, setError]       = useState<string | null>(null);

  async function handleSearch() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setPayload(null);
    try {
      const data = await api.retrieveEvidence({
        top_k: topK,
        program_id: programId ?? undefined,
        channel_id: channelId ?? undefined,
        keywords: query.trim().split(/\s+/),
      });
      setPayload(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Evidence retrieval failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateInsight() {
    if (!payload) return;
    setGen(true);
    setError(null);
    try {
      await api.generateInsight({
        evidence_set_id: payload.evidence_set_id,
        program_id: programId ?? undefined,
      });
      navigate(`/ai/insights`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Insight generation failed');
      setGen(false);
    }
  }

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      <PageHeader
        title="Evidence Explorer"
        description="Retrieve semantically ranked evidence from the comment corpus using natural language queries."
      />
      <ScopeIndicator />
      <GlobalFilterBar />

      {/* Search form */}
      <Card className="space-y-4 border-slate-200">
        <h2 className="text-xs font-semibold text-[var(--color-text-subtle)] uppercase tracking-wider font-mono">
          Evidence Query Parameters
        </h2>
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="e.g. government economic policy accountability"
            className="flex-1 px-4 py-2 rounded-lg border border-slate-300 bg-white text-xs sm:text-sm text-[var(--color-text-main)] placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <div className="flex items-center gap-2">
            <label className="text-xs text-[var(--color-text-subtle)] whitespace-nowrap">Top K</label>
            <select
              value={topK}
              onChange={e => setTopK(Number(e.target.value))}
              className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-xs font-medium text-slate-800"
            >
              {[5, 10, 20, 30].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <Button
            onClick={handleSearch}
            isLoading={loading}
            variant="primary"
            className="flex items-center justify-center gap-2 shrink-0"
          >
            <Search size={15} />
            Search Evidence
          </Button>
        </div>
        <p className="text-xs text-[var(--color-text-subtle)] leading-relaxed">
          Evidence retrieval uses keyword and semantic matching over verified comment text (`text_clean`).
          Raw comments (`text_raw`), author hashes, and PII are strictly excluded.
        </p>
      </Card>

      {/* Error display */}
      {error && (
        <div className="flex items-center gap-3 p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
          <AlertCircle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Results payload */}
      {payload && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 border border-slate-200 rounded-lg">
            <div>
              <p className="text-xs sm:text-sm font-semibold text-[var(--color-text-main)]">
                {payload.evidence_count} evidence items retrieved
                {payload.total_matching_count > payload.evidence_count && (
                  <span className="text-[var(--color-text-subtle)] font-normal">
                    {' '}(of {payload.total_matching_count} total matching)
                  </span>
                )}
              </p>
              <p className="text-[11px] text-[var(--color-text-subtle)] font-mono mt-0.5">
                Method: {payload.retrieval_method} • ID: {payload.evidence_set_id.slice(0, 8)}…
              </p>
            </div>
            <Button
              onClick={handleGenerateInsight}
              isLoading={generating}
              variant="secondary"
              className="flex items-center gap-2"
            >
              <Lightbulb size={15} />
              Generate Insight from Evidence
            </Button>
          </div>

          {/* Evidence table */}
          <EvidenceTable items={payload.evidence_items} />
        </div>
      )}
    </div>
  );
};

export default EvidenceExplorerPage;
