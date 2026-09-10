import React, { useState } from 'react';
import { ThumbsUp, Calendar, ShieldAlert } from 'lucide-react';
import { Badge } from '../ui/Badge';
import { formatDate } from '../../lib/formatters';
import { TOPIC_LABELS, STANCE_LABELS } from '../../lib/constants';
import type { EvidenceItemOut } from '../../types/api';

interface EvidenceTableProps {
  items: EvidenceItemOut[];
  onSelectEvidence?: (item: EvidenceItemOut) => void;
}

export const EvidenceTable: React.FC<EvidenceTableProps> = ({ items, onSelectEvidence }) => {
  const [selectedItem, setSelectedItem] = useState<EvidenceItemOut | null>(null);

  const handleRowClick = (item: EvidenceItemOut) => {
    setSelectedItem(item);
    onSelectEvidence?.(item);
  };

  return (
    <div className="space-y-4">
      {/* Privacy Notice Banner */}
      <div className="flex items-center gap-2 p-3 bg-slate-50 border border-slate-200 text-slate-700 rounded-lg text-xs">
        <ShieldAlert size={15} className="text-amber-600 shrink-0" />
        <span>
          <strong className="font-semibold text-slate-900">Privacy Enforcement:</strong> Comment text displayed below uses anonymized clean text (<code className="font-mono text-[11px] bg-slate-100 px-1 py-0.5 rounded text-slate-800">text_clean</code>). Author hashes, usernames, and raw uncleaned text are permanently excluded from all API payload schemas.
        </span>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto border border-slate-200 rounded-[var(--radius-card)] bg-white shadow-xs">
        <table className="w-full text-left text-xs text-[var(--color-text-main)]">
          <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-[var(--color-text-muted)] uppercase tracking-wider text-[11px]">
            <tr>
              <th className="p-3 w-12 text-center">Rank</th>
              <th className="p-3">Cleaned Comment Text</th>
              <th className="p-3">Source Program</th>
              <th className="p-3">Topic</th>
              <th className="p-3">Stance</th>
              <th className="p-3 text-right">Relevance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((item) => (
              <tr
                key={item.evidence_id || item.comment_id}
                onClick={() => handleRowClick(item)}
                className="hover:bg-slate-50/80 cursor-pointer transition-colors"
              >
                <td className="p-3 text-center font-mono font-semibold text-blue-600">
                  #{item.rank}
                </td>
                <td className="p-3 max-w-md">
                  <p className="line-clamp-2 font-body font-normal text-[var(--color-text-main)] leading-relaxed">
                    &quot;{item.text_clean}&quot;
                  </p>
                  <div className="flex items-center gap-3 mt-1 text-[11px] text-[var(--color-text-subtle)] font-mono">
                    <span className="flex items-center gap-1">
                      <Calendar size={11} /> {formatDate(item.posted_at)}
                    </span>
                    <span className="flex items-center gap-1">
                      <ThumbsUp size={11} /> {item.like_count} likes
                    </span>
                  </div>
                </td>
                <td className="p-3 whitespace-nowrap">
                  <p className="font-semibold text-[var(--color-text-main)]">{item.program_name}</p>
                  <p className="text-[11px] text-[var(--color-text-subtle)]">{item.channel_name}</p>
                </td>
                <td className="p-3 whitespace-nowrap">
                  <Badge variant="outline" size="sm">
                    {TOPIC_LABELS[item.layer2_topic] || item.layer2_topic}
                  </Badge>
                  <p className="text-[10px] text-[var(--color-text-subtle)] mt-0.5 font-mono">
                    {(item.layer2_confidence * 100).toFixed(0)}% conf
                  </p>
                </td>
                <td className="p-3 whitespace-nowrap">
                  <Badge
                    variant={
                      item.layer4_stance === 'STANCE_CRIT'
                        ? 'crit'
                        : item.layer4_stance === 'STANCE_SUPP'
                        ? 'supp'
                        : 'neut'
                    }
                    size="sm"
                  >
                    {STANCE_LABELS[item.layer4_stance] || item.layer4_stance}
                  </Badge>
                  <p className="text-[10px] text-[var(--color-text-subtle)] mt-0.5 font-mono">
                    {(item.layer4_confidence * 100).toFixed(0)}% conf
                  </p>
                </td>
                <td className="p-3 text-right font-mono font-bold text-blue-600 whitespace-nowrap">
                  {(item.relevance_score * 100).toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Slide-over Evidence Detail Modal */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex justify-end">
          <div className="w-full max-w-lg bg-white h-full p-6 shadow-2xl overflow-y-auto space-y-6 flex flex-col border-l border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="font-heading font-bold text-base text-[var(--color-text-main)]">
                Evidence Provenance Detail
              </h3>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-slate-400 hover:text-slate-700 text-sm font-bold w-7 h-7 rounded-full flex items-center justify-center hover:bg-slate-100"
              >
                ✕
              </button>
            </div>

            {/* Context Chain */}
            <div className="space-y-2.5 bg-slate-50 p-3.5 rounded-lg border border-slate-200 text-xs">
              <p className="font-semibold text-slate-700 uppercase tracking-wider text-[10px] font-mono">
                Provenential Chain
              </p>
              <div className="space-y-1 font-mono text-[11px] text-slate-800">
                <p>📺 Channel: <span className="font-semibold">{selectedItem.channel_name}</span></p>
                <p>↳ 🎬 Program: <span className="font-semibold">{selectedItem.program_name}</span></p>
                <p>   ↳ 📹 Video Title: <span className="font-semibold">{selectedItem.video_title || selectedItem.video_id}</span></p>
                <p>      ↳ 💬 Comment ID: <span className="text-blue-600">{selectedItem.comment_id}</span></p>
              </div>
            </div>

            {/* Comment Body */}
            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold text-[var(--color-text-subtle)] uppercase font-mono">
                Cleaned Comment Content (text_clean)
              </p>
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs sm:text-sm leading-relaxed text-slate-900 font-medium">
                &quot;{selectedItem.text_clean}&quot;
              </div>
            </div>

            {/* Classification Scores */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-1">
                <p className="text-[11px] text-[var(--color-text-subtle)]">Macro Topic (Layer 2)</p>
                <p className="font-bold text-[var(--color-text-main)]">
                  {TOPIC_LABELS[selectedItem.layer2_topic] || selectedItem.layer2_topic}
                </p>
                <p className="text-[11px] text-emerald-700 font-mono">
                  Confidence: {(selectedItem.layer2_confidence * 100).toFixed(1)}%
                </p>
              </div>

              <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-1">
                <p className="text-[11px] text-[var(--color-text-subtle)]">Stance Orientation (Layer 4)</p>
                <p className="font-bold text-[var(--color-text-main)]">
                  {STANCE_LABELS[selectedItem.layer4_stance] || selectedItem.layer4_stance}
                </p>
                <p className="text-[11px] text-emerald-700 font-mono">
                  Confidence: {(selectedItem.layer4_confidence * 100).toFixed(1)}%
                </p>
              </div>
            </div>

            {/* Relevance & Metadata */}
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1 font-mono">
              <p className="text-slate-600">Retrieval Score: <strong className="text-slate-900">{(selectedItem.relevance_score * 100).toFixed(2)}%</strong></p>
              <p className="text-slate-600">Posted At: <strong className="text-slate-900">{formatDate(selectedItem.posted_at)}</strong></p>
              <p className="text-slate-600">Likes: <strong className="text-slate-900">{selectedItem.like_count}</strong></p>
            </div>

            <div className="mt-auto pt-4 border-t border-slate-200">
              <button
                onClick={() => setSelectedItem(null)}
                className="w-full py-2 bg-[var(--color-primary-500)] text-white rounded-lg text-xs font-semibold hover:bg-[var(--color-primary-600)] transition-colors"
              >
                Close Provenance Panel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
