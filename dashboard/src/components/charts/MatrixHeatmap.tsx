import React, { useState } from 'react';
import { TOPIC_LABELS, STANCE_LABELS } from '../../lib/constants';
import { formatNumber, formatPercent } from '../../lib/formatters';
import { EmptyState } from '../ui/EmptyState';
import { Grid } from 'lucide-react';

interface MatrixHeatmapProps {
  matrix: Record<string, Record<string, number>>;
  title?: string;
}

export const MatrixHeatmap: React.FC<MatrixHeatmapProps> = ({
  matrix,
  title = 'Topic × Stance Matrix Heatmap',
}) => {
  const [mode, setMode] = useState<'count' | 'row_pct' | 'col_pct'>('count');

  if (!matrix || Object.keys(matrix).length === 0) {
    return (
      <EmptyState
        icon={Grid}
        title="No Matrix Data"
        description="Cross-tabulated Topic × Stance data is unavailable for the selected filter scope."
      />
    );
  }

  const topics = ['TOPIC_ECON_SERV', 'TOPIC_FOR', 'TOPIC_GOV', 'TOPIC_LAW', 'TOPIC_MEDIA'];
  const stances = ['STANCE_CRIT', 'STANCE_NEUT', 'STANCE_SUPP'];

  // Calculate totals and find peak cell
  let grandTotal = 0;
  let maxCellVal = 0;
  let peakTopic = '';
  let peakStance = '';
  let peakCount = 0;

  const rowTotals: Record<string, number> = {};
  const colTotals: Record<string, number> = {};

  stances.forEach((s) => (colTotals[s] = 0));

  topics.forEach((t) => {
    rowTotals[t] = 0;
    const rowObj = matrix[t] || {};
    stances.forEach((s) => {
      const val = rowObj[s] || 0;
      rowTotals[t] += val;
      colTotals[s] += val;
      grandTotal += val;
      if (val > maxCellVal) {
        maxCellVal = val;
      }
      if (val > peakCount) {
        peakCount = val;
        peakTopic = t;
        peakStance = s;
      }
    });
  });

  // Restrained Blue/Slate Color intensity helper
  const getCellBg = (val: number) => {
    if (val === 0 || maxCellVal === 0) return 'bg-slate-50 text-slate-400';
    const ratio = val / maxCellVal;
    if (ratio > 0.75) return 'bg-blue-600 text-white font-bold';
    if (ratio > 0.5) return 'bg-blue-500 text-white font-semibold';
    if (ratio > 0.25) return 'bg-blue-100 text-blue-900 font-medium';
    return 'bg-blue-50/60 text-blue-900';
  };

  const peakTopicLabel = TOPIC_LABELS[peakTopic] || peakTopic;
  const peakStanceLabel = STANCE_LABELS[peakStance] || peakStance;
  const peakPct = grandTotal > 0 ? (peakCount / grandTotal) * 100 : 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-2">
        <h3 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
          {title}
        </h3>
        {/* Toggle Mode */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs self-start sm:self-auto border border-slate-200">
          <button
            onClick={() => setMode('count')}
            className={`px-2.5 py-0.5 rounded font-medium transition-colors ${
              mode === 'count' ? 'bg-white text-[var(--color-text-main)] shadow-xs' : 'text-[var(--color-text-subtle)]'
            }`}
          >
            Count
          </button>
          <button
            onClick={() => setMode('row_pct')}
            className={`px-2.5 py-0.5 rounded font-medium transition-colors ${
              mode === 'row_pct' ? 'bg-white text-[var(--color-text-main)] shadow-xs' : 'text-[var(--color-text-subtle)]'
            }`}
          >
            Row %
          </button>
          <button
            onClick={() => setMode('col_pct')}
            className={`px-2.5 py-0.5 rounded font-medium transition-colors ${
              mode === 'col_pct' ? 'bg-white text-[var(--color-text-main)] shadow-xs' : 'text-[var(--color-text-subtle)]'
            }`}
          >
            Col %
          </button>
        </div>
      </div>

      {/* Grid Table */}
      <div className="overflow-x-auto border border-[var(--color-border)] rounded-lg">
        <table className="w-full text-center text-xs border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-[var(--color-border)] text-[var(--color-text-muted)] font-semibold">
              <th className="p-2.5 text-left w-48 font-medium">Macro Topic</th>
              {stances.map((s) => (
                <th key={s} className="p-2.5 font-medium">
                  {STANCE_LABELS[s]}
                </th>
              ))}
              <th className="p-2.5 bg-slate-100 font-bold">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {topics.map((t) => {
              const rTotal = rowTotals[t] || 0;
              return (
                <tr key={t}>
                  <td className="p-2.5 text-left font-semibold text-[var(--color-text-main)] bg-slate-50">
                    {TOPIC_LABELS[t]}
                  </td>
                  {stances.map((s) => {
                    const count = matrix[t]?.[s] || 0;
                    const cTotal = colTotals[s] || 0;
                    let displayVal = formatNumber(count);
                    if (mode === 'row_pct') {
                      displayVal = formatPercent(rTotal > 0 ? count / rTotal : 0);
                    } else if (mode === 'col_pct') {
                      displayVal = formatPercent(cTotal > 0 ? count / cTotal : 0);
                    }

                    return (
                      <td
                        key={s}
                        className={`p-2.5 font-mono transition-colors ${getCellBg(count)}`}
                        title={`${TOPIC_LABELS[t]} × ${STANCE_LABELS[s]}: ${count} comments`}
                      >
                        {displayVal}
                      </td>
                    );
                  })}
                  <td className="p-2.5 bg-slate-100 font-bold text-slate-800 font-mono">
                    {formatNumber(rTotal)}
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr className="bg-slate-100 font-bold text-slate-900 border-t border-[var(--color-border)]">
              <td className="p-2.5 text-left">Total Valid Comments</td>
              {stances.map((s) => (
                <td key={s} className="p-2.5 font-mono">
                  {formatNumber(colTotals[s])}
                </td>
              ))}
              <td className="p-2.5 font-mono text-blue-700 font-bold">
                {formatNumber(grandTotal)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Automated Analytical Signal */}
      {grandTotal > 0 && (
        <div className="p-3 bg-blue-50/60 border border-blue-100 rounded-lg text-xs text-blue-900">
          <strong className="font-semibold">Analytical Signal:</strong> The dominant topic-stance cell in this scope is{' '}
          <strong>{peakTopicLabel} × {peakStanceLabel}</strong> with{' '}
          <strong>{formatNumber(peakCount)} comments</strong> ({peakPct.toFixed(1)}% of all valid scope comments).
        </div>
      )}
    </div>
  );
};
