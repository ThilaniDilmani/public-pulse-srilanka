import React from 'react';
import { PageHeader } from '../../components/layout/PageHeader';
import { ScopeIndicator } from '../../components/layout/ScopeIndicator';
import { GlobalFilterBar } from '../../components/filters/GlobalFilterBar';
import { Card } from '../../components/ui/Card';
import { KPICard } from '../../components/shared/KPICard';
import { KPICardSkeleton, ChartSkeleton } from '../../components/ui/Skeleton';
import { useDataQuality } from '../../hooks/useAnalytics';
import { formatPercent, formatNumber } from '../../lib/formatters';
import { CheckCircle, XCircle, AlertTriangle, Database, TrendingUp } from 'lucide-react';

/* ── Quality bar ────────────────────────────────────────── */
function QualityBar({
  label,
  passed,
  total,
  color = '#16A34A',
}: {
  label: string;
  passed: number;
  total: number;
  color?: string;
}) {
  const pct = total > 0 ? passed / total : 0;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-[var(--color-text-subtle)]">{label}</span>
        <span className="font-mono font-semibold" style={{ color }}>
          {formatPercent(pct)} ({formatNumber(passed)} / {formatNumber(total)})
        </span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(pct * 100, 100)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export const DataQualityPage: React.FC = () => {
  const { data, isLoading, isError } = useDataQuality();

  const total   = data?.overview?.total_comments ?? 0;
  const valid   = data?.overview?.valid_comments ?? 0;
  const noise   = data?.overview?.noise_comments ?? 0;
  const pending = data?.overview?.pending_comments ?? 0;

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      <PageHeader
        title="Data Quality & Health"
        description="Corpus health metrics: pipeline pass rates, classification confidence, and comment validation statistics."
      />
      <ScopeIndicator />
      <GlobalFilterBar />

      {isLoading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => <KPICardSkeleton key={i} />)}
          </div>
          <ChartSkeleton />
        </div>
      ) : isError || !data ? (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
          <AlertTriangle size={16} className="shrink-0" />
          <span>Failed to load data quality metrics.</span>
        </div>
      ) : (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPICard
              title="Total Comments"
              value={total}
              subtitle="In corpus"
              icon={<Database size={18} />}
            />
            <KPICard
              title="Valid Comments"
              value={formatPercent(total > 0 ? valid / total : 0)}
              subtitle={`${formatNumber(valid)} passed validation`}
              icon={<CheckCircle size={18} />}
            />
            <KPICard
              title="Noise Comments"
              value={formatPercent(total > 0 ? noise / total : 0)}
              subtitle={`${formatNumber(noise)} filtered`}
              icon={<XCircle size={18} />}
            />
            <KPICard
              title="Avg Comments/Video"
              value={data.overview.avg_comments_per_video.toFixed(1)}
              subtitle={`Across ${formatNumber(data.overview.total_videos)} videos`}
              icon={<TrendingUp size={18} />}
            />
          </div>

          {/* Pipeline pass rates */}
          <Card className="space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-subtle)] font-mono border-b border-slate-100 pb-2">
              Pipeline Pass Rates
            </h2>
            <QualityBar
              label="Validation Rate (valid / total)"
              passed={valid}
              total={total}
              color="#16A34A"
            />
            <QualityBar
              label="Noise Rate (noise / total)"
              passed={noise}
              total={total}
              color="#DC2626"
            />
            {pending > 0 && (
              <QualityBar
                label="Pending Classification (pending / total)"
                passed={pending}
                total={total}
                color="#D4AC0D"
              />
            )}
          </Card>

          {/* Corpus scope stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="space-y-1 text-center">
              <p className="text-[11px] uppercase tracking-wider text-[var(--color-text-subtle)] font-mono">Videos</p>
              <p className="font-mono text-2xl font-bold text-[var(--color-text-main)]">
                {formatNumber(data.overview.total_videos)}
              </p>
            </Card>
            <Card className="space-y-1 text-center">
              <p className="text-[11px] uppercase tracking-wider text-[var(--color-text-subtle)] font-mono">Programs</p>
              <p className="font-mono text-2xl font-bold text-[var(--color-text-main)]">
                {formatNumber(data.overview.total_programs)}
              </p>
            </Card>
            <Card className="space-y-1 text-center">
              <p className="text-[11px] uppercase tracking-wider text-[var(--color-text-subtle)] font-mono">Channels</p>
              <p className="font-mono text-2xl font-bold text-[var(--color-text-main)]">
                {formatNumber(data.overview.total_channels)}
              </p>
            </Card>
            <Card className="space-y-1 text-center">
              <p className="text-[11px] uppercase tracking-wider text-[var(--color-text-subtle)] font-mono">Noise Rate</p>
              <p className="font-mono text-2xl font-bold text-[var(--color-text-main)]">
                {formatPercent(data.overview.noise_rate)}
              </p>
            </Card>
          </div>

          {/* Classification confidence by layer */}
          {data.average_confidence_by_layer &&
            Object.keys(data.average_confidence_by_layer).length > 0 && (
            <Card className="space-y-4">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-subtle)] font-mono border-b border-slate-100 pb-2">
                Average Classification Confidence by Layer
              </h2>
              {Object.entries(data.average_confidence_by_layer).map(([layer, conf]) => (
                <QualityBar
                  key={layer}
                  label={layer}
                  passed={Math.round(conf * 1000)}
                  total={1000}
                  color="#2563EB"
                />
              ))}
              <p className="text-xs text-[var(--color-text-subtle)] pt-1 leading-relaxed">
                Confidence is the fine-tuned XLM-R model&apos;s predicted probability for assigned classes.
                Values above 0.80 indicate high-confidence predictions.
              </p>
            </Card>
          )}
        </>
      )}
    </div>
  );
};

export default DataQualityPage;
