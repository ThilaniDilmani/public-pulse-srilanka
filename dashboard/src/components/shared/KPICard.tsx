import React from 'react';
import { Card } from '../ui/Card';
import { formatNumber } from '../../lib/formatters';

interface KPICardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  trendText?: string;
  trendIsPositive?: boolean;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  accentColor?: string;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  trendText,
  trendIsPositive,
  icon,
  badge,
  accentColor,
}) => {
  return (
    <Card className="relative overflow-hidden bg-white border border-[var(--color-border)] p-4 sm:p-5 shadow-[var(--shadow-xs)]">
      {accentColor && (
        <div
          className="absolute top-0 left-0 right-0 h-0.5"
          style={{ backgroundColor: accentColor }}
        />
      )}
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-subtle)]">
            {title}
          </p>
          <div className="text-2xl sm:text-3xl font-bold font-heading text-[var(--color-text-main)] tracking-tight">
            {typeof value === 'number' ? formatNumber(value) : value}
          </div>

          {trendText && (
            <div className="flex items-center gap-1 text-xs font-medium pt-0.5">
              <span className={trendIsPositive === false ? 'text-rose-600' : 'text-emerald-600'}>
                {trendText}
              </span>
            </div>
          )}

          {subtitle && !trendText && (
            <p className="text-xs text-[var(--color-text-subtle)] leading-relaxed pt-0.5">
              {subtitle}
            </p>
          )}
        </div>

        <div className="flex flex-col items-end gap-2 shrink-0">
          {icon && (
            <div className="p-2 bg-slate-50 border border-slate-100 rounded-lg text-slate-600">
              {icon}
            </div>
          )}
          {badge}
        </div>
      </div>
    </Card>
  );
};
