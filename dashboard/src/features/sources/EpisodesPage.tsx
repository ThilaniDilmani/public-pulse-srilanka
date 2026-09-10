import React, { useState } from 'react';
import { Film, Calendar } from 'lucide-react';
import { PageHeader } from '../../components/layout/PageHeader';
import { ScopeIndicator } from '../../components/layout/ScopeIndicator';
import { GlobalFilterBar } from '../../components/filters/GlobalFilterBar';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Skeleton';
import { formatNumber, formatDate } from '../../lib/formatters';
import { TOPIC_LABELS } from '../../lib/constants';
import { useEpisodes } from '../../hooks/useAnalytics';
import { EmptyState } from '../../components/ui/EmptyState';

export const EpisodesPage: React.FC = () => {
  const [page, setPage] = useState(0);
  const limit = 20;

  const { data: episodeData, isLoading } = useEpisodes(limit, page * limit);

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      <PageHeader
        title="Episode / Video Index"
        description="Per-episode analytical summaries including comment volume, top macro-topic, and stance breakdown."
      />

      <GlobalFilterBar />
      <ScopeIndicator />

      <Card padding="none" className="overflow-hidden border border-slate-200">
        {isLoading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} height={36} width="100%" />
            ))}
          </div>
        ) : episodeData?.items && episodeData.items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-[var(--color-text-muted)] uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="p-3">Episode Title</th>
                  <th className="p-3">Program</th>
                  <th className="p-3">Published Date</th>
                  <th className="p-3 text-right">Total Comments</th>
                  <th className="p-3 text-right">Valid Comments</th>
                  <th className="p-3 text-right">Noise Exit %</th>
                  <th className="p-3">Dominant Topic</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {episodeData.items.map((ep) => (
                  <tr key={ep.video_id} className="hover:bg-slate-50/80">
                    <td className="p-3 font-semibold text-[var(--color-text-main)] max-w-xs">
                      <div className="flex items-center gap-2">
                        <Film size={14} className="text-blue-600 shrink-0" />
                        <span className="truncate" title={ep.title || ''}>{ep.title || ep.video_id}</span>
                      </div>
                    </td>
                    <td className="p-3 font-medium text-[var(--color-text-muted)]">
                      {ep.program_name}
                    </td>
                    <td className="p-3 whitespace-nowrap text-[var(--color-text-subtle)] font-mono">
                      <span className="inline-flex items-center gap-1">
                        <Calendar size={11} /> {formatDate(ep.published_at)}
                      </span>
                    </td>
                    <td className="p-3 text-right font-mono font-semibold">
                      {formatNumber(ep.total_comments)}
                    </td>
                    <td className="p-3 text-right font-mono text-emerald-700 font-semibold">
                      {formatNumber(ep.valid_comments)}
                    </td>
                    <td className="p-3 text-right font-mono text-amber-700">
                      {(ep.noise_rate * 100).toFixed(1)}%
                    </td>
                    <td className="p-3">
                      {ep.top_topic ? (
                        <Badge variant="outline" size="sm">
                          {TOPIC_LABELS[ep.top_topic] || ep.top_topic}
                        </Badge>
                      ) : (
                        <span className="text-[10px] text-slate-400">N/A</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={Film}
            title="No Episodes Found"
            description="No episode records are available for the selected filter scope."
          />
        )}

        {/* Pagination Bar */}
        {episodeData && episodeData.total > 0 && (
          <div className="p-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs">
            <span className="text-slate-600">
              Showing page <strong className="font-semibold text-slate-900">{page + 1}</strong> of <strong className="font-semibold text-slate-900">{Math.ceil(episodeData.total / limit)}</strong> ({episodeData.total} total episodes)
            </span>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(p - 1, 0))}
                disabled={page === 0}
                className="px-3 py-1 bg-white border border-slate-200 rounded-md font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40 shadow-xs"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={(page + 1) * limit >= episodeData.total}
                className="px-3 py-1 bg-white border border-slate-200 rounded-md font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40 shadow-xs"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

export default EpisodesPage;
