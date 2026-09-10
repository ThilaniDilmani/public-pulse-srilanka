import React from 'react';
import { PageHeader } from '../../components/layout/PageHeader';
import { ScopeIndicator } from '../../components/layout/ScopeIndicator';
import { GlobalFilterBar } from '../../components/filters/GlobalFilterBar';
import { TopicBarChart } from '../../components/charts/TopicBarChart';
import { EntityGroupedBar } from '../../components/charts/EntityGroupedBar';
import { Card } from '../../components/ui/Card';
import { ChartSkeleton } from '../../components/ui/Skeleton';
import { TOPIC_LABELS } from '../../lib/constants';
import { useTopicDistribution, useEntityMatrix } from '../../hooks/useAnalytics';

export const TopicsPage: React.FC = () => {
  const { data: topics, isLoading: loadingTopics } = useTopicDistribution();
  const { data: programTopics, isLoading: loadingProgTopics } = useEntityMatrix('program', 'topic');
  const { data: channelTopics, isLoading: loadingChanTopics } = useEntityMatrix('channel', 'topic');

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      <PageHeader
        title="Macro-Topic Distribution"
        description="Explore the primary macro-topics classified by XLM-R across monitored news programs."
      />

      <GlobalFilterBar />
      <ScopeIndicator />

      {/* Main Topic Chart */}
      <Card>
        {loadingTopics ? (
          <ChartSkeleton height={220} />
        ) : (
          <TopicBarChart
            distribution={topics?.distribution || []}
            totalComments={topics?.total_valid_comments}
          />
        )}
      </Card>

      {/* Topic Taxonomy Reference Grid */}
      <div className="space-y-3">
        <h3 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
          Macro-Topic Taxonomy Reference
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          {Object.entries(TOPIC_LABELS).map(([key, label]) => (
            <div key={key} className="p-4 bg-white border border-slate-200 rounded-lg space-y-1 shadow-xs">
              <span className="font-mono text-[10px] text-[var(--color-primary-500)] font-bold">{key}</span>
              <p className="font-bold text-[var(--color-text-main)]">{label}</p>
              <p className="text-[var(--color-text-subtle)] text-[11px] leading-relaxed">
                Classified by fine-tuned XLM-RoBERTa model. Preprocessed via Unicode NFC normalization.
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Program & Channel Comparisons */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          {loadingProgTopics ? (
            <ChartSkeleton height={240} />
          ) : (
            <EntityGroupedBar
              matrix={programTopics?.matrix || {}}
              entityType="program"
              matrixType="topic"
            />
          )}
        </Card>

        <Card>
          {loadingChanTopics ? (
            <ChartSkeleton height={240} />
          ) : (
            <EntityGroupedBar
              matrix={channelTopics?.matrix || {}}
              entityType="channel"
              matrixType="topic"
            />
          )}
        </Card>
      </div>
    </div>
  );
};

export default TopicsPage;
