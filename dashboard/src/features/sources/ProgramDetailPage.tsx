import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layers, ArrowLeft, Tv } from 'lucide-react';
import { PageHeader } from '../../components/layout/PageHeader';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { KPICard } from '../../components/shared/KPICard';
import { TopicBarChart } from '../../components/charts/TopicBarChart';
import { StanceDonut } from '../../components/charts/StanceDonut';
import { MatrixHeatmap } from '../../components/charts/MatrixHeatmap';
import { VolumeAreaChart } from '../../components/charts/VolumeAreaChart';
import { InsightCard } from '../../components/shared/InsightCard';
import { ChartSkeleton } from '../../components/ui/Skeleton';
import { EmptyState } from '../../components/ui/EmptyState';
import {
  useProgramDetail,
  useOverviewKPIs,
  useTopicDistribution,
  useStanceDistribution,
  useTopicStanceMatrix,
  useVolumeOverTime,
  useInsights,
  useEpisodes,
} from '../../hooks/useAnalytics';

type TabType = 'overview' | 'topics' | 'stance' | 'matrix' | 'volume' | 'insights' | 'episodes';

export const ProgramDetailPage: React.FC = () => {
  const { programId } = useParams<{ programId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const { data: program } = useProgramDetail(programId);
  const { data: overview, isLoading: loadingOverview } = useOverviewKPIs({ program_id: programId });
  const { data: topics, isLoading: loadingTopics } = useTopicDistribution({ program_id: programId });
  const { data: stances, isLoading: loadingStances } = useStanceDistribution(null, { program_id: programId });
  const { data: matrix, isLoading: loadingMatrix } = useTopicStanceMatrix({ program_id: programId });
  const { data: volume, isLoading: loadingVolume } = useVolumeOverTime('daily', { program_id: programId });
  const { data: insights } = useInsights(programId);
  const { data: episodes } = useEpisodes(10, 0);

  if (!program && !loadingOverview) {
    return (
      <div className="p-8 text-center space-y-4 max-w-md mx-auto">
        <p className="text-sm text-[var(--color-text-subtle)]">Program not found.</p>
        <button onClick={() => navigate('/sources/programs')} className="text-xs font-semibold text-[var(--color-primary-500)] underline">
          Back to Programs List
        </button>
      </div>
    );
  }

  const tabs: { id: TabType; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'topics', label: 'Topics' },
    { id: 'stance', label: 'Stance' },
    { id: 'matrix', label: 'Topic × Stance' },
    { id: 'volume', label: 'Volume Trend' },
    { id: 'insights', label: 'AI Insights' },
    { id: 'episodes', label: 'Episodes' },
  ];

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      <button
        onClick={() => navigate('/sources/programs')}
        className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--color-primary-500)] hover:underline"
      >
        <ArrowLeft size={14} /> Back to Programs List
      </button>

      {/* Header */}
      <PageHeader
        title={program?.name || 'Program Detail'}
        description={`Hosted under ${program?.channel_name} (${program?.platform})`}
        actions={
          <Badge variant="outline" size="md">
            <Tv size={12} className="mr-1 text-slate-500" /> {program?.channel_name}
          </Badge>
        }
      />

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 overflow-x-auto gap-2 text-xs font-medium">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-3.5 py-2 border-b-2 transition-colors whitespace-nowrap ${
              activeTab === t.id
                ? 'border-[var(--color-primary-500)] text-[var(--color-primary-500)] font-bold'
                : 'border-transparent text-[var(--color-text-subtle)] hover:text-[var(--color-text-main)]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content Panels */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <KPICard title="Program Scraped Comments" value={overview?.total_comments || 0} icon={<Layers size={18} />} />
            <KPICard title="Valid Scored Comments" value={overview?.valid_comments || 0} icon={<Layers size={18} />} />
            <KPICard title="Noise Exit Rate" value={`${((overview?.noise_rate || 0) * 100).toFixed(1)}%`} icon={<Layers size={18} />} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              {loadingTopics ? <ChartSkeleton height={200} /> : <TopicBarChart distribution={topics?.distribution || []} title={`${program?.name} — Topic Distribution`} />}
            </Card>
            <Card>
              {loadingStances ? <ChartSkeleton height={200} /> : <StanceDonut distribution={stances?.distribution || []} title={`${program?.name} — Stance Distribution`} />}
            </Card>
          </div>
        </div>
      )}

      {activeTab === 'topics' && (
        <Card>
          {loadingTopics ? <ChartSkeleton height={240} /> : <TopicBarChart distribution={topics?.distribution || []} title={`${program?.name} — Topic Breakdown`} totalComments={topics?.total_valid_comments} />}
        </Card>
      )}

      {activeTab === 'stance' && (
        <Card>
          {loadingStances ? <ChartSkeleton height={240} /> : <StanceDonut distribution={stances?.distribution || []} title={`${program?.name} — Stance Breakdown`} totalValid={stances?.total_valid_comments} />}
        </Card>
      )}

      {activeTab === 'matrix' && (
        <Card>
          {loadingMatrix ? <ChartSkeleton height={260} /> : <MatrixHeatmap matrix={matrix?.matrix || {}} title={`${program?.name} — Topic × Stance Matrix`} />}
        </Card>
      )}

      {activeTab === 'volume' && (
        <Card>
          {loadingVolume ? <ChartSkeleton height={240} /> : <VolumeAreaChart dataPoints={volume?.data_points || []} title={`${program?.name} — Volume Trend`} />}
        </Card>
      )}

      {activeTab === 'insights' && (
        <div className="space-y-4">
          <h3 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
            AI Insights generated for {program?.name}
          </h3>
          {insights && insights.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {insights.map((ins) => (
                <InsightCard key={ins.insight_id} insight={ins} onSelect={(id) => navigate(`/ai/insights/${id}`)} />
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Layers}
              title="No Program Insights"
              description={`No grounded AI insights generated yet for ${program?.name}.`}
            />
          )}
        </div>
      )}

      {activeTab === 'episodes' && (
        <Card padding="none" className="overflow-hidden border border-slate-200">
          <div className="p-3 border-b border-slate-100 bg-slate-50 font-bold text-xs text-[var(--color-text-main)]">
            Recent Episodes for {program?.name}
          </div>
          <div className="divide-y divide-slate-100 text-xs">
            {episodes?.items.map((ep) => (
              <div key={ep.video_id} className="p-3.5 flex items-center justify-between hover:bg-slate-50">
                <div>
                  <p className="font-semibold text-[var(--color-text-main)]">{ep.title}</p>
                  <p className="text-[11px] text-[var(--color-text-subtle)] mt-0.5">
                    Published: {ep.published_at ? ep.published_at.slice(0, 10) : 'N/A'} • {ep.total_comments} comments
                  </p>
                </div>
                <Badge variant="outline" size="sm">Top: {ep.top_topic || 'N/A'}</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

export default ProgramDetailPage;
