import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Tv, ExternalLink, Layers, Users, Search } from 'lucide-react';
import { PageHeader } from '../../components/layout/PageHeader';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Skeleton } from '../../components/ui/Skeleton';
import { formatNumber } from '../../lib/formatters';
import { useChannels } from '../../hooks/useAnalytics';
import { EmptyState } from '../../components/ui/EmptyState';

export const ChannelsPage: React.FC = () => {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const { data: channels, isLoading } = useChannels();

  const filtered = channels?.filter(c => c.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      <PageHeader
        title="Monitored TV Channels"
        description="YouTube news channels cataloged and monitored by Public Pulse for Sri Lankan civic discourse tracking."
      />

      {/* Search Bar */}
      <div className="flex items-center gap-3 bg-white border border-[var(--color-border)] rounded-[var(--radius-card)] p-3 shadow-xs max-w-md">
        <Search size={16} className="text-slate-400 shrink-0" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search channel name..."
          className="w-full text-xs text-[var(--color-text-main)] placeholder-slate-400 bg-transparent focus:outline-none"
        />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="p-5 bg-white border border-slate-200 rounded-lg space-y-3">
              <Skeleton height={20} width="60%" />
              <Skeleton height={14} width="80%" />
              <Skeleton height={32} width="100%" />
            </div>
          ))}
        </div>
      ) : filtered && filtered.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((channel) => (
            <Card key={channel.id} className="space-y-4 flex flex-col justify-between hover:border-slate-300">
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 bg-blue-50 text-blue-600 rounded-lg border border-blue-100">
                      <Tv size={18} />
                    </div>
                    <h3 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
                      {channel.name}
                    </h3>
                  </div>
                </div>

                {channel.description && (
                  <p className="text-xs text-[var(--color-text-subtle)] line-clamp-2 leading-relaxed">
                    {channel.description}
                  </p>
                )}

                <div className="flex items-center gap-4 text-xs text-[var(--color-text-muted)] pt-2 border-t border-slate-100">
                  {channel.subscriber_count !== undefined && channel.subscriber_count !== null && (
                    <span className="flex items-center gap-1 font-mono text-[11px]">
                      <Users size={12} className="text-slate-400" /> {formatNumber(channel.subscriber_count)} subscribers
                    </span>
                  )}
                  <span className="flex items-center gap-1 text-[11px]">
                    <Layers size={12} className="text-slate-400" /> YouTube
                  </span>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between gap-2 border-t border-slate-100">
                {channel.channel_url ? (
                  <a
                    href={channel.channel_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-slate-500 hover:text-slate-800 hover:underline inline-flex items-center gap-1 font-medium"
                  >
                    YouTube Channel <ExternalLink size={11} />
                  </a>
                ) : <span />}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => navigate(`/sources/channels/${channel.id}`)}
                >
                  View Programs $\rightarrow$
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={Tv}
          title="No Channels Found"
          description={`No channel matching "${search}" was found in the monitored catalog.`}
          actionLabel="Clear Search"
          onAction={() => setSearch('')}
        />
      )}
    </div>
  );
};

export default ChannelsPage;
