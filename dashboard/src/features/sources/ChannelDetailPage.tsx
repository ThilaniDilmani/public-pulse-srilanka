import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Tv, ExternalLink, Layers, ArrowLeft } from 'lucide-react';
import { PageHeader } from '../../components/layout/PageHeader';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { TopicBarChart } from '../../components/charts/TopicBarChart';
import { StanceDonut } from '../../components/charts/StanceDonut';
import { KPICard } from '../../components/shared/KPICard';
import { ChartSkeleton } from '../../components/ui/Skeleton';
import {
  useChannels,
  usePrograms,
  useOverviewKPIs,
  useTopicDistribution,
  useStanceDistribution,
} from '../../hooks/useAnalytics';

export const ChannelDetailPage: React.FC = () => {
  const { channelId } = useParams<{ channelId: string }>();
  const navigate = useNavigate();

  const { data: channels } = useChannels();
  const channel = channels?.find((c) => c.id === channelId);

  const { data: programs } = usePrograms(channelId);
  const { data: overview, isLoading: loadingOverview } = useOverviewKPIs({ channel_id: channelId });
  const { data: topics, isLoading: loadingTopics } = useTopicDistribution({ channel_id: channelId });
  const { data: stances, isLoading: loadingStances } = useStanceDistribution(null, { channel_id: channelId });

  if (!channel && !loadingOverview) {
    return (
      <div className="p-8 text-center space-y-4 max-w-md mx-auto">
        <p className="text-sm text-[var(--color-text-subtle)]">Channel not found.</p>
        <Button onClick={() => navigate('/sources/channels')}>Back to Channels</Button>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      <button
        onClick={() => navigate('/sources/channels')}
        className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--color-primary-500)] hover:underline"
      >
        <ArrowLeft size={14} /> Back to Channels List
      </button>

      <PageHeader
        title={channel?.name || 'Channel Detail'}
        description={channel?.description || 'Monitored YouTube news channel'}
        actions={
          channel?.channel_url ? (
            <a
              href={channel.channel_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-md text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs"
            >
              YouTube Channel <ExternalLink size={12} />
            </a>
          ) : undefined
        }
      />

      {/* KPI Overview Scoped to Channel */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KPICard title="Channel Scraped Comments" value={overview?.total_comments || 0} icon={<Tv size={18} />} />
        <KPICard title="Valid Scored Comments" value={overview?.valid_comments || 0} icon={<Layers size={18} />} />
        <KPICard title="Hosted Programs" value={programs?.length || 0} icon={<Layers size={18} />} />
      </div>

      {/* Hosted Programs List */}
      <div className="space-y-3">
        <h3 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
          Programs Monitored under {channel?.name} ({programs?.length || 0})
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {programs?.map((prog) => (
            <Card key={prog.id} className="p-4 flex items-center justify-between hover:border-slate-300">
              <div>
                <h4 className="font-bold text-sm text-[var(--color-text-main)]">{prog.name}</h4>
                <p className="text-xs text-[var(--color-text-subtle)] mt-0.5">Platform: {prog.platform}</p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => navigate(`/sources/programs/${prog.id}`)}
              >
                Program Detail $\rightarrow$
              </Button>
            </Card>
          ))}
        </div>
      </div>

      {/* Scoped Topic & Stance Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          {loadingTopics ? (
            <ChartSkeleton height={200} />
          ) : (
            <TopicBarChart
              distribution={topics?.distribution || []}
              title={`${channel?.name} — Topic Breakdown`}
            />
          )}
        </Card>

        <Card>
          {loadingStances ? (
            <ChartSkeleton height={200} />
          ) : (
            <StanceDonut
              distribution={stances?.distribution || []}
              title={`${channel?.name} — Stance Breakdown`}
            />
          )}
        </Card>
      </div>
    </div>
  );
};

export default ChannelDetailPage;
