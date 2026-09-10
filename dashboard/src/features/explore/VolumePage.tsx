import React, { useState } from 'react';
import { PageHeader } from '../../components/layout/PageHeader';
import { ScopeIndicator } from '../../components/layout/ScopeIndicator';
import { GlobalFilterBar } from '../../components/filters/GlobalFilterBar';
import { VolumeAreaChart } from '../../components/charts/VolumeAreaChart';
import { Card } from '../../components/ui/Card';
import { ChartSkeleton } from '../../components/ui/Skeleton';
import { formatNumber, formatPercent } from '../../lib/formatters';
import { useVolumeOverTime, usePeriodOverPeriod } from '../../hooks/useAnalytics';

export const VolumePage: React.FC = () => {
  const [granularity, setGranularity] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [periodDays, setPeriodDays] = useState<number>(30);

  const { data: volume, isLoading: loadingVolume } = useVolumeOverTime(granularity);
  const { data: pop, isLoading: loadingPop } = usePeriodOverPeriod(periodDays);

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      <PageHeader
        title="Discourse Volume & Trends"
        description="Analyze public discourse comment volume over time and period-over-period shifts."
      />

      <GlobalFilterBar />
      <ScopeIndicator />

      {/* Main Volume Chart Card */}
      <Card className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div className="space-y-0.5">
            <h3 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
              Comment Volume Time-Series
            </h3>
            <p className="text-xs text-[var(--color-text-subtle)]">
              Granularity: <strong className="text-[var(--color-text-main)]">{granularity.toUpperCase()}</strong>
            </p>
          </div>

          {/* Granularity Selector */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs self-start sm:self-auto border border-slate-200">
            {(['daily', 'weekly', 'monthly'] as const).map((g) => (
              <button
                key={g}
                onClick={() => setGranularity(g)}
                className={`px-3 py-1 rounded-md font-medium capitalize transition-colors ${
                  granularity === g
                    ? 'bg-white text-[var(--color-text-main)] shadow-xs'
                    : 'text-[var(--color-text-subtle)]'
                }`}
              >
                {g}
              </button>
            ))}
          </div>
        </div>

        {loadingVolume ? (
          <ChartSkeleton height={240} />
        ) : (
          <VolumeAreaChart
            dataPoints={volume?.data_points || []}
            granularity={granularity}
          />
        )}
      </Card>

      {/* Period-over-Period Section */}
      <Card className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h3 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
              Period-over-Period Comparison
            </h3>
            <p className="text-xs text-[var(--color-text-subtle)]">
              Comparing current {periodDays}-day window against preceding {periodDays}-day window
            </p>
          </div>

          {/* Window Selector */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs self-start sm:self-auto border border-slate-200">
            {[7, 14, 30, 60, 90].map((days) => (
              <button
                key={days}
                onClick={() => setPeriodDays(days)}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  periodDays === days
                    ? 'bg-white text-[var(--color-text-main)] shadow-xs'
                    : 'text-[var(--color-text-subtle)]'
                }`}
              >
                {days}d
              </button>
            ))}
          </div>
        </div>

        {loadingPop ? (
          <ChartSkeleton height={140} />
        ) : (
          <div className="overflow-x-auto border border-slate-200 rounded-lg">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-[var(--color-text-muted)]">
                <tr>
                  <th className="p-3 font-medium">Metric</th>
                  <th className="p-3 text-right font-medium">Current Period ({periodDays}d)</th>
                  <th className="p-3 text-right font-medium">Previous Period ({periodDays}d)</th>
                  <th className="p-3 text-right font-medium">Change (Δ)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr>
                  <td className="p-3 font-semibold text-[var(--color-text-main)]">Total Scraped Comments</td>
                  <td className="p-3 text-right font-mono">{formatNumber(pop?.current_period?.metrics?.total_comments)}</td>
                  <td className="p-3 text-right font-mono">{formatNumber(pop?.previous_period?.metrics?.total_comments)}</td>
                  <td className="p-3 text-right font-mono font-bold text-blue-600">
                    {pop?.changes?.volume_change_pct !== undefined
                      ? `${pop.changes.volume_change_pct > 0 ? '+' : ''}${pop.changes.volume_change_pct.toFixed(1)}%`
                      : '0%'}
                  </td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold text-[var(--color-text-main)]">Valid Scored Comments</td>
                  <td className="p-3 text-right font-mono">{formatNumber(pop?.current_period?.metrics?.valid_comments)}</td>
                  <td className="p-3 text-right font-mono">{formatNumber(pop?.previous_period?.metrics?.valid_comments)}</td>
                  <td className="p-3 text-right font-mono text-emerald-600 font-bold">—</td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold text-[var(--color-text-main)]">Noise Exit Rate</td>
                  <td className="p-3 text-right font-mono">{formatPercent(pop?.current_period?.metrics?.noise_rate)}</td>
                  <td className="p-3 text-right font-mono">{formatPercent(pop?.previous_period?.metrics?.noise_rate)}</td>
                  <td className="p-3 text-right font-mono font-bold text-amber-600">
                    {pop?.changes?.noise_rate_change !== undefined
                      ? `${pop.changes.noise_rate_change > 0 ? '+' : ''}${(pop.changes.noise_rate_change * 100).toFixed(1)}%`
                      : '0%'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};

export default VolumePage;
