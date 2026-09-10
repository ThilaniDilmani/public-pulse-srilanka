import React from 'react';
import { ShieldCheck, AlertTriangle, CheckCircle, XCircle, Ban, HelpCircle } from 'lucide-react';
import { Badge } from '../ui/Badge';
import { Card } from '../ui/Card';
import { formatPercent } from '../../lib/formatters';
import type { VerificationReportOut, ClaimVerificationOut } from '../../types/api';

interface VerificationReportProps {
  report: VerificationReportOut;
}

export const VerificationReport: React.FC<VerificationReportProps> = ({ report }) => {
  const getVerdictBadge = (label: ClaimVerificationOut['label']) => {
    switch (label) {
      case 'SUPPORTED':
        return (
          <Badge variant="supported">
            <CheckCircle size={12} className="mr-1" /> SUPPORTED
          </Badge>
        );
      case 'PARTIALLY_SUPPORTED':
        return (
          <Badge variant="partially_supported">
            <AlertTriangle size={12} className="mr-1" /> PARTIAL
          </Badge>
        );
      case 'UNSUPPORTED':
        return (
          <Badge variant="unsupported">
            <XCircle size={12} className="mr-1" /> UNSUPPORTED
          </Badge>
        );
      case 'CONTRADICTED':
        return (
          <Badge variant="contradicted">
            <Ban size={12} className="mr-1" /> CONTRADICTED
          </Badge>
        );
      default:
        return <Badge variant="outline">{label}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Metric Gauges Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 bg-white border border-[var(--color-border)] rounded-lg text-center">
          <p className="text-[11px] text-[var(--color-text-subtle)] font-medium">Grounding Score</p>
          <p className="text-xl font-bold font-heading text-[var(--color-primary-500)] mt-0.5">
            {formatPercent(report.grounding_score)}
          </p>
        </div>

        <div className="p-3 bg-white border border-[var(--color-border)] rounded-lg text-center">
          <p className="text-[11px] text-[var(--color-text-subtle)] font-medium">Claim Support Rate</p>
          <p className="text-xl font-bold font-heading text-emerald-600 mt-0.5">
            {formatPercent(report.claim_support_rate)}
          </p>
        </div>

        <div className="p-3 bg-white border border-[var(--color-border)] rounded-lg text-center">
          <p className="text-[11px] text-[var(--color-text-subtle)] font-medium">Contradiction Rate</p>
          <p className="text-xl font-bold font-heading text-rose-600 mt-0.5">
            {formatPercent(report.contradiction_rate)}
          </p>
        </div>

        <div className="p-3 bg-white border border-[var(--color-border)] rounded-lg text-center">
          <p className="text-[11px] text-[var(--color-text-subtle)] font-medium">Citation Precision</p>
          <p className="text-xl font-bold font-heading text-blue-600 mt-0.5">
            {formatPercent(report.evidence_citation_precision)}
          </p>
        </div>
      </div>

      {/* Claim Breakdown Table */}
      <Card padding="none" className="overflow-hidden">
        <div className="p-4 bg-[var(--color-surface-subtle)] border-b border-[var(--color-border)] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck size={18} className="text-[var(--color-primary-500)]" />
            <h4 className="font-heading font-bold text-sm text-[var(--color-text-main)]">
              Atomic Claim Verification Breakdown ({report.total_claims_evaluated} claims)
            </h4>
          </div>
          <span className="text-xs text-[var(--color-text-subtle)] font-mono">
            Method: {report.verifier_method}
          </span>
        </div>

        <div className="divide-y divide-[var(--color-border)] text-xs">
          {report.claim_verifications.map((claim) => (
            <div key={claim.claim_id} className="p-4 space-y-2 hover:bg-[var(--color-surface-hover)]">
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <span className="font-mono text-[10px] font-bold text-[var(--color-text-subtle)]">
                    {claim.claim_id} (Finding {claim.finding_id})
                  </span>
                  <p className="text-sm font-medium text-[var(--color-text-main)]">
                    "{claim.claim_text}"
                  </p>
                </div>
                <div className="shrink-0">{getVerdictBadge(claim.label)}</div>
              </div>

              <div className="text-xs text-[var(--color-text-muted)] bg-slate-50 p-2.5 rounded border border-slate-200">
                <strong>Verification Rationale:</strong> {claim.reason}
              </div>

              {claim.evidence_ids && claim.evidence_ids.length > 0 && (
                <div className="text-[11px] text-[var(--color-text-subtle)] flex items-center gap-2">
                  <span>Cites {claim.evidence_ids.length} Evidence Items:</span>
                  <div className="flex flex-wrap gap-1">
                    {claim.evidence_ids.map((id) => (
                      <span key={id} className="font-mono text-[10px] bg-slate-200 text-slate-800 px-1.5 py-0.5 rounded">
                        {id.slice(0, 8)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Explanation Banner */}
      <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs text-[var(--color-text-subtle)] space-y-1">
        <p className="font-semibold text-[var(--color-text-main)] flex items-center gap-1">
          <HelpCircle size={14} /> Understanding Faithfulness Scores
        </p>
        <p>
          Faithfulness verification evaluates generated findings at the atomic claim level against retrieved evidence.
          <strong> Grounding Score</strong> represents the weighted support ratio across evaluated claims. Claims marked 
          <strong className="text-rose-700"> CONTRADICTED</strong> indicate AI statements directly refuted by the underlying comment evidence.
        </p>
      </div>
    </div>
  );
};
