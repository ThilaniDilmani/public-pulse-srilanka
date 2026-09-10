import React from 'react';
import { STANCE_LABELS, STANCE_COLORS } from '../../lib/constants';
import { formatNumber, formatPercent } from '../../lib/formatters';
import type { StanceDistributionItem } from '../../types/api';
import { EmptyState } from '../ui/EmptyState';
import { Compass } from 'lucide-react';

interface StanceDonutProps {
  distribution: StanceDistributionItem[];
  title?: string;
  totalValid?: number;
}

export const StanceDonut: React.FC<StanceDonutProps> = ({
  distribution,
  title = 'Stance Distribution',
  totalValid,
}) => {
  if (!distribution || distribution.length === 0) {
    return (
      <EmptyState
        icon={Compass}
        title="No Stance Data"
        description="No stance classifications are available for the selected filter scope."
      />
    );
  }

  const grandTotal = totalValid || distribution.reduce((sum, item) => sum + item.count, 0);
  
  // Calculate SVG arc paths
  const radius = 58;
  const strokeWidth = 16;
  const circumference = 2 * Math.PI * radius;

  let accumulatedOffset = 0;
  const slices = distribution.map((item) => {
    const fraction = grandTotal > 0 ? item.count / grandTotal : 0;
    const strokeDasharray = `${fraction * circumference} ${circumference}`;
    const strokeDashoffset = -accumulatedOffset;
    accumulatedOffset += fraction * circumference;
    const color = STANCE_COLORS[item.stance] || '#64748B';
    const label = STANCE_LABELS[item.stance] || item.stance;
    return { ...item, fraction, strokeDasharray, strokeDashoffset, color, label };
  });

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between border-b border-slate-100 pb-2">
        <h3 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
          {title}
        </h3>
        <span className="text-[11px] text-[var(--color-text-subtle)] font-medium">
          Orientation toward subject matter
        </span>
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-around gap-6 py-2">
        {/* SVG Donut */}
        <div className="relative w-36 h-36 shrink-0">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 160 160">
            <circle
              cx="80"
              cy="80"
              r={radius}
              fill="transparent"
              stroke="#F1F5F9"
              strokeWidth={strokeWidth}
            />
            {slices.map((slice) => (
              <circle
                key={slice.stance}
                cx="80"
                cy="80"
                r={radius}
                fill="transparent"
                stroke={slice.color}
                strokeWidth={strokeWidth}
                strokeDasharray={slice.strokeDasharray}
                strokeDashoffset={slice.strokeDashoffset}
                className="transition-all duration-500 ease-out hover:opacity-85"
              />
            ))}
          </svg>
          {/* Center text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-2">
            <span className="text-xl font-bold font-heading text-[var(--color-text-main)] tracking-tight">
              {formatNumber(grandTotal)}
            </span>
            <span className="text-[10px] text-[var(--color-text-subtle)] font-medium">
              Valid Comments
            </span>
          </div>
        </div>

        {/* Legend */}
        <div className="space-y-3 w-full sm:w-auto text-xs">
          {slices.map((slice) => (
            <div key={slice.stance} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: slice.color }} />
                <span className="font-medium text-[var(--color-text-main)]">{slice.label}</span>
              </div>
              <span className="font-mono text-[var(--color-text-muted)] text-[11px]">
                <strong>{formatNumber(slice.count)}</strong> ({formatPercent(slice.fraction)})
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
