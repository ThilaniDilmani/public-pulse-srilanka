import React, { useState } from 'react';
import { Info } from 'lucide-react';
import { PageHeader } from '../../components/layout/PageHeader';
import { ScopeIndicator } from '../../components/layout/ScopeIndicator';
import { GlobalFilterBar } from '../../components/filters/GlobalFilterBar';
import { StanceDonut } from '../../components/charts/StanceDonut';
import { EntityGroupedBar } from '../../components/charts/EntityGroupedBar';
import { Card } from '../../components/ui/Card';
import { ChartSkeleton } from '../../components/ui/Skeleton';
import { TOPIC_LABELS, STANCE_DISCLAIMER } from '../../lib/constants';
import { useStanceDistribution, useEntityMatrix } from '../../hooks/useAnalytics';

export const StancePage: React.FC = () => {
  const [topicFilter, setTopicFilter] = useState<string | null>(null);

  const { data: stances, isLoading: loadingStances } = useStanceDistribution(topicFilter);
  const { data: programStances, isLoading: loadingProgStances } = useEntityMatrix('program', 'stance');
  const { data: channelStances, isLoading: loadingChanStances } = useEntityMatrix('channel', 'stance');

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      <PageHeader
        title="Stance Orientation"
        description="Analyze comment orientation (Critical, Neutral, Supportive) classified by XLM-R."
      />

      <GlobalFilterBar />
      <ScopeIndicator />

      {/* Scientific Disclaimer Banner */}
      <div className="flex items-start gap-3 p-3.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700">
        <Info size={16} className="text-blue-600 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong className="font-semibold text-slate-900">Scientific Notice:</strong> {STANCE_DISCLAIMER} STANCE_CRIT captures critical orientation; sarcasm is merged into STANCE_CRIT and is not presented as an independent dimension.
        </p>
      </div>

      {/* Main Stance Card with Topic Filter */}
      <Card className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <h3 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
            Stance Distribution
          </h3>

          {/* Topic Filter Dropdown */}
          <div className="flex items-center gap-2 text-xs">
            <span className="font-medium text-[var(--color-text-subtle)]">Filter by Topic:</span>
            <select
              value={topicFilter || ''}
              onChange={(e) => setTopicFilter(e.target.value || null)}
              className="bg-slate-50 border border-slate-200 rounded-[var(--radius-input)] px-2.5 py-1 font-medium text-[var(--color-text-main)] focus:bg-white"
            >
              <option value="">All Topics</option>
              {Object.entries(TOPIC_LABELS).map(([k, label]) => (
                <option key={k} value={k}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loadingStances ? (
          <ChartSkeleton height={220} />
        ) : (
          <StanceDonut
            distribution={stances?.distribution || []}
            totalValid={stances?.total_valid_comments}
          />
        )}
      </Card>

      {/* Program & Channel Stance Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          {loadingProgStances ? (
            <ChartSkeleton height={240} />
          ) : (
            <EntityGroupedBar
              matrix={programStances?.matrix || {}}
              entityType="program"
              matrixType="stance"
            />
          )}
        </Card>

        <Card>
          {loadingChanStances ? (
            <ChartSkeleton height={240} />
          ) : (
            <EntityGroupedBar
              matrix={channelStances?.matrix || {}}
              entityType="channel"
              matrixType="stance"
            />
          )}
        </Card>
      </div>
    </div>
  );
};

export default StancePage;
