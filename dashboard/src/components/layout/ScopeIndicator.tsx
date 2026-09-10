import React from 'react';
import { Filter, X } from 'lucide-react';
import { useFilterStore } from '../../store/filterStore';
import { useChannels, usePrograms } from '../../hooks/useAnalytics';

export const ScopeIndicator: React.FC = () => {
  const { channelId, programId, videoId, startDate, endDate, setChannel, setProgram, setVideo, setDateRange, clearAll } =
    useFilterStore();

  const { data: channels } = useChannels();
  const { data: programs } = usePrograms();

  const activeChannel = channels?.find((c) => c.id === channelId);
  const activeProgram = programs?.find((p) => p.id === programId);

  const hasFilters = Boolean(channelId || programId || videoId || startDate || endDate);

  if (!hasFilters) {
    return (
      <div className="flex items-center gap-2 text-xs text-[var(--color-text-subtle)] bg-[var(--color-surface-subtle)] px-3 py-1.5 rounded-[var(--radius-pill)] border border-[var(--color-border)]">
        <Filter size={14} className="text-[var(--color-text-subtle)]" />
        <span>Active Scope: <strong className="text-[var(--color-text-main)]">All Programs • All Channels • All Time</strong></span>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className="font-semibold text-[var(--color-text-muted)] flex items-center gap-1">
        <Filter size={14} /> Active Scope:
      </span>

      {activeChannel && (
        <span className="inline-flex items-center gap-1.5 bg-[var(--color-primary-100)] text-[var(--color-primary-700)] px-2.5 py-1 rounded-[var(--radius-pill)] font-medium">
          Channel: {activeChannel.name}
          <button onClick={() => setChannel(null)} className="hover:opacity-75"><X size={12} /></button>
        </span>
      )}

      {activeProgram && (
        <span className="inline-flex items-center gap-1.5 bg-[var(--color-accent-100)] text-[var(--color-accent-700)] px-2.5 py-1 rounded-[var(--radius-pill)] font-medium">
          Program: {activeProgram.name}
          <button onClick={() => setProgram(null)} className="hover:opacity-75"><X size={12} /></button>
        </span>
      )}

      {videoId && (
        <span className="inline-flex items-center gap-1.5 bg-slate-100 text-slate-800 px-2.5 py-1 rounded-[var(--radius-pill)] font-medium">
          Video ID: {videoId.slice(0, 8)}…
          <button onClick={() => setVideo(null)} className="hover:opacity-75"><X size={12} /></button>
        </span>
      )}

      {(startDate || endDate) && (
        <span className="inline-flex items-center gap-1.5 bg-blue-50 text-blue-800 px-2.5 py-1 rounded-[var(--radius-pill)] font-medium">
          Range: {startDate || 'Start'} to {endDate || 'Present'}
          <button onClick={() => setDateRange(null, null)} className="hover:opacity-75"><X size={12} /></button>
        </span>
      )}

      <button
        onClick={clearAll}
        className="text-[var(--color-primary-500)] hover:underline ml-1 font-medium text-xs"
      >
        Clear all filters
      </button>
    </div>
  );
};
