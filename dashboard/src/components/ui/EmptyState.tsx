import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';
import { Button } from './Button';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  reason?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  description,
  reason,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center bg-white border border-[var(--color-border)] rounded-[var(--radius-card)] shadow-[var(--shadow-xs)] ${className}`}>
      <div className="w-10 h-10 rounded-full bg-[var(--color-surface-hover)] border border-[var(--color-border-subtle)] flex items-center justify-center text-[var(--color-text-subtle)] mb-3">
        <Icon size={20} />
      </div>
      
      <h3 className="text-sm font-semibold text-[var(--color-text-main)] mb-1">
        {title}
      </h3>
      
      <p className="text-xs text-[var(--color-text-muted)] max-w-sm mb-2 leading-relaxed">
        {description}
      </p>

      {reason && (
        <span className="inline-block text-[11px] text-[var(--color-text-subtle)] bg-[var(--color-surface-sunken)] px-2.5 py-1 rounded-[var(--radius-pill)] mb-3 font-mono">
          Note: {reason}
        </span>
      )}

      {actionLabel && onAction && (
        <Button size="sm" variant="outline" onClick={onAction} className="mt-1">
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
