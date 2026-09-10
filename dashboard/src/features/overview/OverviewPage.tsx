import React from 'react';
import { useNavigate } from 'react-router-dom';
import { MessageSquare, CheckCircle, ShieldAlert, Film, TrendingUp, Sparkles, ShieldCheck, ArrowRight } from 'lucide-react';
import { PageHeader } from '../../components/layout/PageHeader';
import { ScopeIndicator } from '../../components/layout/ScopeIndicator';
import { GlobalFilterBar } from '../../components/filters/GlobalFilterBar';
import { KPICard } from '../../components/shared/KPICard';
import { InsightCard } from '../../components/shared/InsightCard';
import { TopicBarChart } from '../../components/charts/TopicBarChart';
import { StanceDonut } from '../../components/charts/StanceDonut';
import { VolumeAreaChart } from '../../components/charts/VolumeAreaChart';
import { MatrixHeatmap } from '../../components/charts/MatrixHeatmap';
import { EntityGroupedBar } from '../../components/charts/EntityGroupedBar';
import { Card } from '../../components/ui/Card';
import { KPICardSkeleton, ChartSkeleton } from '../../components/ui/Skeleton';
import { formatPercent, formatNumber } from '../../lib/formatters';
import {
  useOverviewKPIs,
  useVolumeOverTime,
  useTopicDistribution,
  useStanceDistribution,
  useTopicStanceMatrix,
  useEntityMatrix,
  usePeriodOverPeriod,
  useInsights,
  useFaithfulnessAnalytics,
} from '../../hooks/useAnalytics';

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: overview, isLoading: loadingOverview } = useOverviewKPIs();
  const { data: volumeData, isLoading: loadingVolume } = useVolumeOverTime('daily');
  const { data: topics, isLoading: loadingTopics } = useTopicDistribution();
  const { data: stances, isLoading: loadingStances } = useStanceDistribution();
  const { data: matrix, isLoading: loadingMatrix } = useTopicStanceMatrix();
  const { data: programMatrix, isLoading: loadingProgMatrix } = useEntityMatrix('program', 'topic');
  const { data: pop, isLoading: loadingPop } = usePeriodOverPeriod(30);
  const { data: insights } = useInsights();
  const { data: faithfulness } = useFaithfulnessAnalytics();

  const volumeChangePct = pop?.changes?.volume_change_pct;

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      {/* 1. Page Identity */}
      <PageHeader
        title="Civic Discourse Overview"
        description="Ground-truth public discourse tracking from Sri Lankan TV news YouTube comments."
      />

      {/* 2. Global Filters */}
      <GlobalFilterBar />
      <ScopeIndicator />

      {/* 3. Key Metrics (Minimal & Contextual with Period-over-Period trend) */}
      {loadingOverview ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICardSkeleton />
          <KPICardSkeleton />
          <KPICardSkeleton />
          <KPICardSkeleton />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            title="Comments Analyzed"
            value={overview?.total_comments || 0}
            trendText={volumeChangePct !== undefined ? `${volumeChangePct >= 0 ? '↑' : '↓'} ${Math.abs(volumeChangePct).toFixed(1)}% vs previous 30d` : undefined}
            trendIsPositive={volumeChangePct !== undefined ? volumeChangePct >= 0 : undefined}
            subtitle="Scraped across monitored TV programs"
            icon={<MessageSquare size={18} />}
          />
          <KPICard
            title="Valid Scored Comments"
            value={overview?.valid_comments || 0}
            subtitle="Passed Layer 1 validation filter"
            icon={<CheckCircle size={18} />}
          />
          <KPICard
            title="Noise Exit Rate"
            value={formatPercent(overview?.noise_rate || 0)}
            subtitle={`${formatNumber(overview?.noise_comments || 0)} comments filtered out`}
            icon={<ShieldAlert size={18} />}
          />
          <KPICard
            title="Avg Comments / Episode"
            value={overview?.avg_comments_per_video?.toFixed(0) || '0'}
            subtitle={`Across ${formatNumber(overview?.total_videos || 0)} analyzed episodes`}
            icon={<Film size={18} />}
          />
        </div>
      )}

      {/* 4. Discussion Volume Hero Visualization */}
      <Card variant="default">
        {loadingVolume ? (
          <ChartSkeleton height={220} />
        ) : (
          <VolumeAreaChart
            dataPoints={volumeData?.data_points || []}
            title="Discussion Volume & Trend Over Time"
          />
        )}
      </Card>

      {/* 5. Topic + Stance Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card variant="default">
          {loadingTopics ? (
            <ChartSkeleton height={200} />
          ) : (
            <TopicBarChart
              distribution={topics?.distribution || []}
              totalComments={topics?.total_valid_comments}
            />
          )}
        </Card>

        <Card variant="default">
          {loadingStances ? (
            <ChartSkeleton height={200} />
          ) : (
            <StanceDonut
              distribution={stances?.distribution || []}
              totalValid={stances?.total_valid_comments}
            />
          )}
        </Card>
      </div>

      {/* 6. Topic × Stance Matrix */}
      <Card variant="default">
        {loadingMatrix ? (
          <ChartSkeleton height={260} />
        ) : (
          <MatrixHeatmap matrix={matrix?.matrix || {}} />
        )}
      </Card>

      {/* 7. Program/Source Analysis & Period Delta Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card variant="default" className="lg:col-span-2">
          {loadingProgMatrix ? (
            <ChartSkeleton height={240} />
          ) : (
            <EntityGroupedBar
              matrix={programMatrix?.matrix || {}}
              entityType="program"
              matrixType="topic"
            />
          )}
        </Card>

        {/* 30-Day Window Analytics Summary */}
        <Card variant="default" className="space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
            <TrendingUp size={16} className="text-[var(--color-primary-500)]" />
            <h3 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
              Period Analytics (30-Day Window)
            </h3>
          </div>

          {loadingPop ? (
            <div className="space-y-2">
              <div className="h-4 skeleton w-full" />
              <div className="h-4 skeleton w-3/4" />
            </div>
          ) : (
            <div className="space-y-3.5 text-xs">
              <div className="p-3 bg-slate-50 border border-slate-100 rounded-lg space-y-1">
                <p className="text-[var(--color-text-subtle)] font-medium">30-Day Volume Change</p>
                <p className="text-xl font-bold font-heading text-[var(--color-primary-500)]">
                  {pop?.changes?.volume_change_pct !== undefined
                    ? `${pop.changes.volume_change_pct > 0 ? '+' : ''}${pop.changes.volume_change_pct.toFixed(1)}%`
                    : '0.0%'}
                </p>
                <p className="text-[11px] text-[var(--color-text-subtle)]">Comparison against preceding 30d window</p>
              </div>

              {faithfulness && (
                <div className="p-3 bg-emerald-50/70 border border-emerald-200/70 rounded-lg space-y-1">
                  <div className="flex items-center gap-1.5 text-emerald-900 font-semibold">
                    <ShieldCheck size={14} className="text-emerald-600" /> Grounding Score
                  </div>
                  <p className="text-xl font-bold text-emerald-700">
                    {formatPercent(faithfulness.mean_grounding_score)}
                  </p>
                  <p className="text-[11px] text-emerald-800">
                    Across {faithfulness.total_verifications} verified AI insights
                  </p>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* 8. AI Intelligence Spotlight */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles size={18} className="text-[var(--color-brand-gold)]" />
            <h3 className="font-heading font-bold text-base text-[var(--color-text-main)]">
              Grounded AI Discourse Insights
            </h3>
          </div>
          <button
            onClick={() => navigate('/ai/insights')}
            className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--color-primary-500)] hover:text-[var(--color-primary-600)] hover:underline"
          >
            View All Insights <ArrowRight size={13} />
          </button>
        </div>

        {insights && insights.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {insights.slice(0, 3).map((ins) => (
              <InsightCard
                key={ins.insight_id}
                insight={ins}
                onSelect={(id) => navigate(`/ai/insights/${id}`)}
              />
            ))}
          </div>
        ) : (
          <Card className="text-center p-8 text-xs text-[var(--color-text-subtle)] bg-white border border-[var(--color-border)]">
            No AI insights generated yet for this scope. Navigate to <strong>AI Intelligence $\rightarrow$ Insights</strong> to generate grounded summaries.
          </Card>
        )}
      </div>
    </div>
  );
};

export default OverviewPage;
