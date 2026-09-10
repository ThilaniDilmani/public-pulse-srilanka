import React from 'react';
import { Sparkles, Calendar, Layers, ShieldCheck, ArrowRight } from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { StatusPill } from '../ui/StatusPill';
import { formatDate } from '../../lib/formatters';
import type { InsightOut } from '../../types/api';

interface InsightCardProps {
  insight: InsightOut;
  onSelect?: (insightId: string) => void;
}

export const InsightCard: React.FC<InsightCardProps> = ({ insight, onSelect }) => {
  return (
    <Card
      className="hover:border-slate-300 hover:shadow-[var(--shadow-hover)] transition-all cursor-pointer space-y-3.5 bg-white border border-slate-200 p-4 font-sans"
      onClick={() => onSelect?.(insight.insight_id)}
    >
      {/* Top Meta Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <div className="p-1 bg-amber-50 text-amber-700 rounded border border-amber-200">
            <Sparkles size={13} />
          </div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-amber-900 font-mono">
            {insight.insight_type.replace(/_/g, ' ')}
          </span>
          {insight.program_id && (
            <Badge variant="outline" size="sm">
              <Layers size={10} className="mr-1 text-slate-400" /> Program Scoped
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <StatusPill status={insight.generation_status} />
          <span className="text-[11px] text-[var(--color-text-subtle)] flex items-center gap-1 font-mono">
            <Calendar size={11} /> {formatDate(insight.generated_at)}
          </span>
        </div>
      </div>

      {/* Summary Excerpt */}
      <div className="space-y-2">
        <p className="text-xs sm:text-sm font-medium text-[var(--color-text-main)] line-clamp-3 leading-relaxed">
          {insight.summary || 'Summary pending grounded LLM generation…'}
        </p>

        {insight.findings && insight.findings.length > 0 && (
          <div className="text-xs text-[var(--color-text-muted)] bg-slate-50 p-2.5 rounded-lg border border-slate-100 flex items-center justify-between">
            <span className="text-[11px]">
              Contains <strong className="text-slate-900 font-semibold">{insight.findings.length} atomic findings</strong> backed by evidence
            </span>
            <ShieldCheck size={14} className="text-emerald-600 shrink-0" />
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="pt-2 flex items-center justify-between text-xs text-[var(--color-primary-500)] font-medium border-t border-slate-100">
        <span className="text-[11px] text-slate-500 font-mono">Model: {insight.llm_model || 'Gemini'}</span>
        <span className="inline-flex items-center gap-1 hover:underline text-xs">
          Inspect Insight & Evidence <ArrowRight size={12} />
        </span>
      </div>
    </Card>
  );
};
