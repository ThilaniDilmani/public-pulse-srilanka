import React from 'react';
import { TOPIC_LABELS, TOPIC_COLORS, STANCE_LABELS, STANCE_COLORS } from '../../lib/constants';
import { formatNumber } from '../../lib/formatters';
import { EmptyState } from '../ui/EmptyState';
import { Layers } from 'lucide-react';

interface EntityGroupedBarProps {
  matrix: Record<string, Record<string, number>>;
  entityType: 'program' | 'channel';
  matrixType: 'topic' | 'stance';
  title?: string;
}

export const EntityGroupedBar: React.FC<EntityGroupedBarProps> = ({
  matrix,
  entityType,
  matrixType,
  title,
}) => {
  if (!matrix || Object.keys(matrix).length === 0) {
    return (
      <EmptyState
        icon={Layers}
        title="No Comparative Data"
        description={`Comparative ${entityType} breakdown data is unavailable for the selected filter scope.`}
      />
    );
  }

  const entities = Object.keys(matrix).slice(0, 6); // Top 6 entities
  const labels = matrixType === 'topic'
    ? ['TOPIC_ECON_SERV', 'TOPIC_FOR', 'TOPIC_GOV', 'TOPIC_LAW', 'TOPIC_MEDIA']
    : ['STANCE_CRIT', 'STANCE_NEUT', 'STANCE_SUPP'];

  const labelMap = matrixType === 'topic' ? TOPIC_LABELS : STANCE_LABELS;
  const colorMap = matrixType === 'topic' ? TOPIC_COLORS : STANCE_COLORS;

  const headingText = title || `Comparative ${entityType === 'program' ? 'Program' : 'Channel'} Breakdown by ${matrixType === 'topic' ? 'Topic' : 'Stance'}`;

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between border-b border-slate-100 pb-2">
        <h3 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
          {headingText}
        </h3>
      </div>

      <div className="space-y-3 text-xs">
        {entities.map((entityName) => {
          const rowData = matrix[entityName] || {};
          const rowTotal = Object.values(rowData).reduce((a, b) => a + b, 0);

          return (
            <div key={entityName} className="space-y-1.5 p-3 bg-white border border-[var(--color-border)] rounded-lg shadow-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-[var(--color-text-main)] truncate max-w-xs">{entityName}</span>
                <span className="font-mono text-[var(--color-text-muted)] text-[11px]">
                  Valid: <strong>{formatNumber(rowTotal)}</strong>
                </span>
              </div>

              {/* Stacked Proportional Bar */}
              {rowTotal > 0 ? (
                <div className="h-3.5 w-full bg-slate-100 rounded-md overflow-hidden flex">
                  {labels.map((lblKey) => {
                    const cnt = rowData[lblKey] || 0;
                    if (cnt === 0) return null;
                    const pct = (cnt / rowTotal) * 100;
                    const color = colorMap[lblKey] || '#64748B';
                    return (
                      <div
                        key={lblKey}
                        className="h-full transition-all duration-300 hover:opacity-85"
                        style={{ width: `${pct}%`, backgroundColor: color }}
                        title={`${labelMap[lblKey] || lblKey}: ${cnt} (${pct.toFixed(1)}%)`}
                      />
                    );
                  })}
                </div>
              ) : (
                <div className="h-3.5 w-full bg-slate-50 rounded-md text-[10px] text-center text-slate-400 flex items-center justify-center">
                  No predictions recorded
                </div>
              )}
            </div>
          );
        })}

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-slate-100 text-xs">
          {labels.map((lblKey) => (
            <div key={lblKey} className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: colorMap[lblKey] }} />
              <span className="text-[var(--color-text-muted)] font-medium text-[11px]">{labelMap[lblKey] || lblKey}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
