import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layers, Search, CheckCircle2, XCircle } from 'lucide-react';
import { PageHeader } from '../../components/layout/PageHeader';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/Skeleton';
import { usePrograms, useChannels } from '../../hooks/useAnalytics';
import { EmptyState } from '../../components/ui/EmptyState';

export const ProgramsPage: React.FC = () => {
  const navigate = useNavigate();
  const [channelFilter, setChannelFilter] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const { data: channels } = useChannels();
  const { data: programs, isLoading } = usePrograms(channelFilter);

  const filtered = programs?.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.channel_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      <PageHeader
        title="Monitored TV Programs"
        description="The primary Sri Lankan TV news programs tracked and classified by Public Pulse."
      />

      {/* Filter & Search Bar */}
      <div className="bg-white border border-[var(--color-border)] rounded-[var(--radius-card)] p-3 sm:p-3.5 shadow-xs flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[200px] relative">
          <Search size={15} className="absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search programs by name or channel…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-[var(--radius-input)] pl-9 pr-3 py-1.5 text-xs font-medium text-[var(--color-text-main)] focus:bg-white"
          />
        </div>

        <div className="min-w-[180px]">
          <select
            value={channelFilter || ''}
            onChange={(e) => setChannelFilter(e.target.value || null)}
            className="w-full bg-slate-50 border border-slate-200 rounded-[var(--radius-input)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-main)] focus:bg-white"
          >
            <option value="">All Channels</option>
            {channels?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Programs Table */}
      <Card padding="none" className="overflow-hidden border border-slate-200">
        {isLoading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} height={32} width="100%" />
            ))}
          </div>
        ) : filtered && filtered.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-[var(--color-text-muted)] uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="p-3">Program Name</th>
                  <th className="p-3">Host Channel</th>
                  <th className="p-3">Platform</th>
                  <th className="p-3 text-center">Status</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((prog) => (
                  <tr
                    key={prog.id}
                    onClick={() => navigate(`/sources/programs/${prog.id}`)}
                    className="hover:bg-slate-50/80 cursor-pointer transition-colors"
                  >
                    <td className="p-3 font-bold text-sm text-[var(--color-text-main)]">
                      <div className="flex items-center gap-2">
                        <Layers size={16} className="text-blue-600 shrink-0" />
                        <span>{prog.name}</span>
                      </div>
                    </td>
                    <td className="p-3 font-medium text-[var(--color-text-muted)]">
                      {prog.channel_name}
                    </td>
                    <td className="p-3 text-[var(--color-text-subtle)] font-mono">
                      {prog.platform}
                    </td>
                    <td className="p-3 text-center whitespace-nowrap">
                      {prog.is_active ? (
                        <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 text-[11px]">
                          <CheckCircle2 size={12} /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full text-[11px]">
                          <XCircle size={12} /> Inactive
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      <span className="text-blue-600 font-semibold hover:underline">
                        Analytics Suite $\rightarrow$
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={Layers}
            title="No Programs Found"
            description="No news programs match the search criteria or channel filter."
            actionLabel="Reset Filters"
            onAction={() => {
              setSearchQuery('');
              setChannelFilter(null);
            }}
          />
        )}
      </Card>
    </div>
  );
};

export default ProgramsPage;
