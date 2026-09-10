import React from 'react';
import { Filter, Calendar, RotateCcw } from 'lucide-react';
import { useFilterStore } from '../../store/filterStore';
import { useChannels, usePrograms } from '../../hooks/useAnalytics';

export const GlobalFilterBar: React.FC = () => {
  const { channelId, programId, startDate, endDate, setChannel, setProgram, setDateRange, clearAll } =
    useFilterStore();

  const { data: channels } = useChannels();
  const { data: programs } = usePrograms(channelId);

  const hasFilters = Boolean(channelId || programId || startDate || endDate);

  return (
    <div className="bg-white border border-[var(--color-border)] rounded-[var(--radius-card)] p-3 sm:p-3.5 shadow-[var(--shadow-xs)] flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-[var(--color-text-main)] shrink-0">
        <Filter size={14} className="text-[var(--color-primary-500)]" />
        <span>Filter Scope:</span>
      </div>

      {/* Channel Select */}
      <div className="flex-1 min-w-[170px] max-w-xs">
        <select
          value={channelId || ''}
          onChange={(e) => setChannel(e.target.value || null)}
          className="w-full bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-[var(--radius-input)] px-2.5 py-1.5 text-xs font-medium text-[var(--color-text-main)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary-500)] focus:bg-white"
          aria-label="Filter by Channel"
        >
          <option value="">All Channels</option>
          {channels?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      {/* Program Select */}
      <div className="flex-1 min-w-[190px] max-w-xs">
        <select
          value={programId || ''}
          onChange={(e) => {
            const selectedProgId = e.target.value || null;
            const progObj = programs?.find((p) => p.id === selectedProgId);
            setProgram(selectedProgId, progObj?.channel_id);
          }}
          className="w-full bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-[var(--radius-input)] px-2.5 py-1.5 text-xs font-medium text-[var(--color-text-main)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary-500)] focus:bg-white"
          aria-label="Filter by Program"
        >
          <option value="">All Programs</option>
          {programs?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} ({p.channel_name})
            </option>
          ))}
        </select>
      </div>

      {/* Date Range Inputs */}
      <div className="flex items-center gap-1.5 text-xs shrink-0 bg-[var(--color-surface-hover)] px-2.5 py-1 rounded-[var(--radius-input)] border border-[var(--color-border)]">
        <Calendar size={13} className="text-[var(--color-text-subtle)]" />
        <input
          type="date"
          value={startDate ? startDate.slice(0, 10) : ''}
          onChange={(e) => setDateRange(e.target.value ? new Date(e.target.value).toISOString() : null, endDate)}
          className="bg-transparent border-0 p-0 text-xs text-[var(--color-text-main)] focus:outline-none"
          aria-label="Start Date"
        />
        <span className="text-[var(--color-text-subtle)] text-[11px]">to</span>
        <input
          type="date"
          value={endDate ? endDate.slice(0, 10) : ''}
          onChange={(e) => setDateRange(startDate, e.target.value ? new Date(e.target.value).toISOString() : null)}
          className="bg-transparent border-0 p-0 text-xs text-[var(--color-text-main)] focus:outline-none"
          aria-label="End Date"
        />
      </div>

      {/* Reset Scope Button */}
      {hasFilters && (
        <button
          onClick={clearAll}
          className="inline-flex items-center gap-1 text-xs font-medium text-[var(--color-primary-500)] hover:text-[var(--color-primary-600)] px-2 py-1 rounded-md hover:bg-blue-50 transition-colors shrink-0 ml-auto"
        >
          <RotateCcw size={12} />
          Reset Scope
        </button>
      )}
    </div>
  );
};
