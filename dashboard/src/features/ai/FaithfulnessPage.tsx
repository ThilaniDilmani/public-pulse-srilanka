import React from 'react';
import { PageHeader } from '../../components/layout/PageHeader';
import { ScopeIndicator } from '../../components/layout/ScopeIndicator';
import { GlobalFilterBar } from '../../components/filters/GlobalFilterBar';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { KPICard } from '../../components/shared/KPICard';
import { KPICardSkeleton } from '../../components/ui/Skeleton';
import { useFaithfulnessAnalytics } from '../../hooks/useAnalytics';
import { formatPercent } from '../../lib/formatters';
import { ShieldCheck, AlertTriangle, TrendingUp, Info } from 'lucide-react';
import { EmptyState } from '../../components/ui/EmptyState';

/* ── Verdict gauge ─────────────────────────────────────── */
function VerdictGauge({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-[var(--color-text-subtle)]">{label}</span>
        <span className="font-mono font-semibold" style={{ color }}>{formatPercent(value)}</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(value * 100, 100)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

/* ── Metric row ────────────────────────────────────────── */
function MetricRow({ label, value, description }: { label: string; value: string; description: string }) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-slate-100 last:border-0">
      <div className="min-w-[180px]">
        <p className="text-xs font-semibold text-[var(--color-text-main)]">{label}</p>
        <p className="font-mono text-base font-bold text-[var(--color-primary-500)]">{value}</p>
      </div>
      <p className="text-xs text-[var(--color-text-subtle)] leading-relaxed pt-0.5">{description}</p>
    </div>
  );
}

export const FaithfulnessPage: React.FC = () => {
  const { data, isLoading, isError } = useFaithfulnessAnalytics();

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      <PageHeader
        title="Faithfulness Analytics"
        description="Aggregate metrics measuring how faithfully grounded LLM insights represent the underlying comment evidence."
      />
      <ScopeIndicator />
      <GlobalFilterBar />

      {/* Methodology note */}
      <div className="flex items-start gap-3 p-3.5 rounded-lg border border-amber-200 bg-amber-50/60 text-xs text-slate-800">
        <Info size={16} className="text-amber-600 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong>Research Note:</strong> Faithfulness is computed per-insight by verifying each atomic claim against retrieved comment evidence. Higher claim support rate and lower unsupported claim rate indicate more grounded generation.
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <KPICardSkeleton key={i} />)}
        </div>
      ) : isError || !data ? (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
          <AlertTriangle size={16} className="shrink-0" />
          <span>Failed to load faithfulness analytics.</span>
        </div>
      ) : (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPICard
              title="Verified Insights"
              value={data.total_verifications}
              subtitle="Total verifications run"
              icon={<ShieldCheck size={18} />}
            />
            <KPICard
              title="Mean Grounding Score"
              value={data.mean_grounding_score.toFixed(3)}
              subtitle="Avg faithfulness (0–1)"
              icon={<TrendingUp size={18} />}
              badge={
                data.mean_grounding_score >= 0.8
                  ? <Badge variant="supported">High</Badge>
                  : data.mean_grounding_score >= 0.5
                  ? <Badge variant="outline">Medium</Badge>
                  : <Badge variant="crit">Low</Badge>
              }
            />
            <KPICard
              title="Mean Support Rate"
              value={formatPercent(data.mean_claim_support_rate)}
              subtitle="Claims fully supported"
            />
            <KPICard
              title="Unsupported Claim Rate"
              value={formatPercent(data.mean_unsupported_claim_rate)}
              subtitle="Claims with no evidence"
            />
          </div>

          {/* Detailed metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Rate gauges */}
            <Card className="space-y-4">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-subtle)] font-mono border-b border-slate-100 pb-2">
                Aggregate Rate Distribution
              </h2>
              <VerdictGauge
                label="Claim Support Rate"
                value={data.mean_claim_support_rate}
                color="#16A34A"
              />
              <VerdictGauge
                label="Partial Support Rate"
                value={data.mean_partial_support_rate}
                color="#D97706"
              />
              <VerdictGauge
                label="Unsupported Claim Rate"
                value={data.mean_unsupported_claim_rate}
                color="#DC2626"
              />
              <VerdictGauge
                label="Contradiction Rate"
                value={data.mean_contradiction_rate}
                color="#7F1D1D"
              />
            </Card>

            {/* Extended metric explanations */}
            <Card className="space-y-0">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-subtle)] font-mono border-b border-slate-100 pb-2 mb-2">
                Quality Metrics Breakdown
              </h2>
              <MetricRow
                label="Mean Grounding Score"
                value={data.mean_grounding_score.toFixed(3)}
                description="Aggregate faithfulness score across all verified insights."
              />
              <MetricRow
                label="Mean Claim Support Rate"
                value={formatPercent(data.mean_claim_support_rate)}
                description="Average fraction of claims fully supported by retrieved evidence per verification."
              />
              <MetricRow
                label="Mean Partial Support Rate"
                value={formatPercent(data.mean_partial_support_rate)}
                description="Average fraction of claims receiving partial support."
              />
              <MetricRow
                label="Unsupported Claim Rate"
                value={formatPercent(data.mean_unsupported_claim_rate)}
                description="Average fraction of claims with no supporting evidence."
              />
              <MetricRow
                label="Mean Citation Precision"
                value={formatPercent(data.mean_citation_precision)}
                description="Average precision of evidence citations."
              />
            </Card>
          </div>

          {data.total_verifications === 0 && (
            <EmptyState
              icon={ShieldCheck}
              title="No Verified Insights Yet"
              description="Generate and verify insights in the AI Intelligence section to view aggregate faithfulness metrics here."
            />
          )}
        </>
      )}
    </div>
  );
};

export default FaithfulnessPage;
