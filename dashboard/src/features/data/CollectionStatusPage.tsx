import React from 'react';
import { PageHeader } from '../../components/layout/PageHeader';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Info, RefreshCw, Calendar } from 'lucide-react';

interface Stage {
  name: string;
  description: string;
  status: 'live' | 'scheduled' | 'manual';
  cadence: string;
  source?: string;
}

const PIPELINE_STAGES: Stage[] = [
  {
    name: 'YouTube Data Ingestion',
    description:
      'Comments are ingested from YouTube via YouTube Data API v3 for targeted Sri Lankan news channels listed in the catalog. ' +
      'Raw comments are stored with video and publish metadata.',
    status: 'manual',
    cadence: 'On-demand / per-collection-run',
    source: 'YouTube Data API v3',
  },
  {
    name: 'Text Pre-processing & Validation',
    description:
      'Raw comment text is cleaned: deduplication, language detection, length filtering, ' +
      'spam heuristics, and Unicode normalisation. Comments passing filters are marked valid=true.',
    status: 'live',
    cadence: 'Runs immediately after ingestion',
  },
  {
    name: 'Topic Classification (Layer 1)',
    description:
      'Each valid comment is classified into one of the 5 macro-topic categories using fine-tuned XLM-RoBERTa.',
    status: 'live',
    cadence: 'Batch — runs after pre-processing completes',
  },
  {
    name: 'Stance Classification (Layer 2)',
    description:
      'Each topic-classified comment receives a stance orientation label: CRITICAL, NEUTRAL, or SUPPORTIVE.',
    status: 'live',
    cadence: 'Batch — runs after topic classification',
  },
  {
    name: 'Evidence Embedding & Indexing',
    description:
      'Valid comments are embedded using a multilingual sentence transformer and indexed for vector similarity retrieval. Only text_clean is embedded.',
    status: 'live',
    cadence: 'Batch — runs after stance classification',
  },
  {
    name: 'Grounded LLM Insight Generation',
    description:
      'On demand, the LLM pipeline retrieves top-k semantically relevant comments, constructs a grounded prompt, and generates structured analytical insights.',
    status: 'manual',
    cadence: 'On-demand via AI Intelligence panel',
  },
  {
    name: 'Atomic Claim Verification',
    description:
      'Generated insights undergo automated claim-by-claim verification against retrieved evidence to compute faithfulness scores.',
    status: 'manual',
    cadence: 'On-demand — triggered from Insight Detail page',
  },
];

const STATUS_BADGES: Record<Stage['status'], JSX.Element> = {
  live:      <Badge variant="supported">Live</Badge>,
  scheduled: <Badge variant="primary">Scheduled</Badge>,
  manual:    <Badge variant="outline">On-demand</Badge>,
};

export const CollectionStatusPage: React.FC = () => {
  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-4xl mx-auto">
      <PageHeader
        title="Collection Status"
        description="Overview of the Public Pulse data collection and processing pipeline architecture."
      />

      <div className="flex items-start gap-3 p-3.5 rounded-lg border border-slate-200 bg-slate-50 text-xs text-slate-700">
        <Info size={16} className="text-blue-600 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          This page describes the 7-stage Public Pulse data processing architecture. Live corpus quality metrics are available on the Data Quality page.
        </p>
      </div>

      <div className="space-y-4">
        {PIPELINE_STAGES.map((stage, i) => (
          <Card key={stage.name} className="space-y-3 border-slate-200">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center shrink-0 font-mono">
                  {i + 1}
                </div>
                <h3 className="text-sm font-semibold text-[var(--color-text-main)]">{stage.name}</h3>
              </div>
              {STATUS_BADGES[stage.status]}
            </div>
            <p className="text-xs text-[var(--color-text-muted)] pl-9 leading-relaxed">{stage.description}</p>
            <div className="pl-9 flex flex-wrap gap-4 text-[11px] text-[var(--color-text-subtle)] font-mono">
              <div className="flex items-center gap-1.5">
                <RefreshCw size={11} />
                {stage.cadence}
              </div>
              {stage.source && (
                <div className="flex items-center gap-1.5">
                  <Calendar size={11} />
                  {stage.source}
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default CollectionStatusPage;
