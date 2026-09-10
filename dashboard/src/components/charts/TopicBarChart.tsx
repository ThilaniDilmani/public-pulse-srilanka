import React from 'react';
import { TOPIC_LABELS, TOPIC_COLORS } from '../../lib/constants';
import { formatNumber, formatPercent } from '../../lib/formatters';
import type { TopicDistributionItem } from '../../types/api';
import { EmptyState } from '../ui/EmptyState';
import { PieChart } from 'lucide-react';

interface TopicBarChartProps {
  distribution: TopicDistributionItem[];
  title?: string;
  totalComments?: number;
}

export const TopicBarChart: React.FC<TopicBarChartProps> = ({
  distribution,
  title = 'Macro-Topic Distribution',
  totalComments,
}) => {
  if (!distribution || distribution.length === 0) {
    return (
      <EmptyState
        icon={PieChart}
        title="No Topic Data"
        description="No topic classifications are available for the selected filter scope."
      />
    );
  }

  const sorted = [...distribution].sort((a, b) => b.count - a.count);
  const maxCount = Math.max(...sorted.map((item) => item.count), 1);

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between border-b border-slate-100 pb-2">
        <h3 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
          {title}
        </h3>
        {totalComments !== undefined && (
          <span className="text-xs text-[var(--color-text-subtle)]">
            Valid: <strong className="font-mono text-[var(--color-text-main)]">{formatNumber(totalComments)}</strong>
          </span>
        )}
      </div>

      <div className="space-y-3.5" role="region" aria-label={title}>
        {sorted.map((item) => {
          const label = TOPIC_LABELS[item.topic] || item.topic;
          const color = TOPIC_COLORS[item.topic] || 'var(--color-primary-500)';
          const pct = item.percentage > 1 ? item.percentage / 100 : item.percentage;
          const widthPct = Math.max((item.count / maxCount) * 100, 3);

          return (
            <div key={item.topic} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-[var(--color-text-main)]">{label}</span>
                <span className="font-mono text-[var(--color-text-muted)] text-[11px]">
                  <strong>{formatNumber(item.count)}</strong> ({formatPercent(pct)})
                </span>
              </div>

              <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden flex">
                <div
                  className="h-full rounded-full transition-all duration-500 ease-out"
                  style={{
                    width: `${widthPct}%`,
                    backgroundColor: color,
                  }}
                  title={`${label}: ${item.count} (${formatPercent(pct)})`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
