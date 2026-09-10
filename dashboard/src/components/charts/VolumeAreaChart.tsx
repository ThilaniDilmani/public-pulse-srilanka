import React from 'react';
import { formatNumber, formatDate } from '../../lib/formatters';
import type { VolumeDataPoint } from '../../types/api';
import { EmptyState } from '../ui/EmptyState';
import { TrendingUp } from 'lucide-react';

interface VolumeAreaChartProps {
  dataPoints: VolumeDataPoint[];
  title?: string;
  granularity?: string;
}

export const VolumeAreaChart: React.FC<VolumeAreaChartProps> = ({
  dataPoints,
  title = 'Comment Volume Trend',
}) => {
  if (!dataPoints || dataPoints.length === 0) {
    return (
      <EmptyState
        icon={TrendingUp}
        title="No Volume Trend Data"
        description="Time-series discussion volume data is unavailable for the selected scope."
      />
    );
  }

  const svgWidth = 600;
  const svgHeight = 200;
  const paddingLeft = 40;
  const paddingBottom = 28;
  const paddingTop = 12;
  const paddingRight = 12;

  const chartW = svgWidth - paddingLeft - paddingRight;
  const chartH = svgHeight - paddingTop - paddingBottom;

  const maxTotal = Math.max(...dataPoints.map((d) => d.total_comments), 1);

  // Map data points to SVG X, Y coordinates
  const points = dataPoints.map((d, idx) => {
    const x = paddingLeft + (idx / Math.max(dataPoints.length - 1, 1)) * chartW;
    const yTotal = paddingTop + chartH - (d.total_comments / maxTotal) * chartH;
    const yValid = paddingTop + chartH - (d.valid_comments / maxTotal) * chartH;
    return { x, yTotal, yValid, dataPoint: d };
  });

  // Create SVG path strings
  const totalPathStr = points.reduce((acc, p, idx) => `${acc} ${idx === 0 ? 'M' : 'L'} ${p.x} ${p.yTotal}`, '');
  const validPathStr = points.reduce((acc, p, idx) => `${acc} ${idx === 0 ? 'M' : 'L'} ${p.x} ${p.yValid}`, '');

  const areaTotalPath = `${totalPathStr} L ${points[points.length - 1].x} ${paddingTop + chartH} L ${points[0].x} ${paddingTop + chartH} Z`;

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between border-b border-slate-100 pb-2">
        <h3 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
          {title}
        </h3>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5 text-[var(--color-primary-500)] font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-primary-500)]" /> Total Scraped
          </span>
          <span className="flex items-center gap-1.5 text-emerald-600 font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-600" /> Valid Scored
          </span>
        </div>
      </div>

      <div className="relative w-full overflow-hidden">
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-auto overflow-visible">
          {/* Subtle Horizontal Grid lines */}
          {[0, 0.33, 0.66, 1].map((ratio) => {
            const y = paddingTop + chartH * (1 - ratio);
            const val = Math.round(maxTotal * ratio);
            return (
              <g key={ratio}>
                <line x1={paddingLeft} y1={y} x2={svgWidth - paddingRight} y2={y} stroke="#F1F5F9" strokeWidth="1" strokeDasharray="3 3" />
                <text x={paddingLeft - 6} y={y + 3} textAnchor="end" fontSize="9" fill="#94A3B8" fontFamily="var(--font-mono)">
                  {formatNumber(val)}
                </text>
              </g>
            );
          })}

          {/* Area Fill Total (Subtle Blue Tint) */}
          <path d={areaTotalPath} fill="#EFF6FF" opacity="0.7" />

          {/* Lines */}
          <path d={totalPathStr} fill="none" stroke="var(--color-primary-500)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <path d={validPathStr} fill="none" stroke="#16A34A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

          {/* X Axis Labels */}
          {points.filter((_, idx) => idx % Math.ceil(points.length / 5) === 0 || idx === points.length - 1).map((p) => (
            <text key={p.dataPoint.date} x={p.x} y={svgHeight - 6} textAnchor="middle" fontSize="9" fill="#64748B" fontFamily="var(--font-mono)">
              {formatDate(p.dataPoint.date)}
            </text>
          ))}
        </svg>
      </div>
    </div>
  );
};
