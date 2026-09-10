import React from 'react';
import clsx from 'clsx';

interface StatusPillProps {
  status: 'pending' | 'running' | 'completed' | 'error' | string;
  label?: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({ status, label }) => {
  const configs: Record<string, { bg: string; text: string; dot: string; defaultLabel: string }> = {
    pending: {
      bg: 'bg-slate-100',
      text: 'text-slate-700',
      dot: 'bg-slate-400',
      defaultLabel: 'Queued',
    },
    running: {
      bg: 'bg-blue-50',
      text: 'text-blue-700',
      dot: 'bg-blue-500 animate-pulse',
      defaultLabel: 'Processing…',
    },
    completed: {
      bg: 'bg-emerald-50',
      text: 'text-emerald-700',
      dot: 'bg-emerald-500',
      defaultLabel: 'Completed',
    },
    error: {
      bg: 'bg-rose-50',
      text: 'text-rose-700',
      dot: 'bg-rose-500',
      defaultLabel: 'Failed',
    },
  };

  const config = configs[status] || configs.pending;

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[var(--radius-pill)] text-xs font-medium border border-transparent',
        config.bg,
        config.text
      )}
    >
      <span className={clsx('w-2 h-2 rounded-full', config.dot)} />
      {label || config.defaultLabel}
    </span>
  );
};
