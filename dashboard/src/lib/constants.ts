/**
 * Authoritative constants for Public Pulse Dashboard.
 *
 * Taxonomies match backend XLM-R classification models:
 * - Layer 1: VALID, NOISE (Utility Gatekeeper)
 * - Layer 2: TOPIC_ECON_SERV, TOPIC_FOR, TOPIC_GOV, TOPIC_LAW, TOPIC_MEDIA (5 Macro Topics)
 * - Layer 4: STANCE_CRIT, STANCE_NEUT, STANCE_SUPP (3 Stance Orientations)
 *
 * Layer 3 (Sub-issue) was permanently removed per documented research scope decision.
 */

export const TOPIC_LABELS: Record<string, string> = {
  TOPIC_ECON_SERV: 'Economics & Services',
  TOPIC_FOR: 'Foreign Affairs',
  TOPIC_GOV: 'Governance',
  TOPIC_LAW: 'Law & Justice',
  TOPIC_MEDIA: 'Media',
};

export const TOPIC_COLORS: Record<string, string> = {
  TOPIC_ECON_SERV: '#1A5276',
  TOPIC_FOR: '#154360',
  TOPIC_GOV: '#7B241C',
  TOPIC_LAW: '#1E8449',
  TOPIC_MEDIA: '#7D3C98',
};

export const STANCE_LABELS: Record<string, string> = {
  STANCE_CRIT: 'Critical',
  STANCE_NEUT: 'Neutral',
  STANCE_SUPP: 'Supportive',
};

export const STANCE_COLORS: Record<string, string> = {
  STANCE_CRIT: '#C0392B',
  STANCE_NEUT: '#7F8C8D',
  STANCE_SUPP: '#27AE60',
};

export const LAYER1_LABELS: Record<string, string> = {
  VALID: 'Valid / Usable',
  NOISE: 'Filtered (Noise)',
};

export const VERDICT_LABELS: Record<string, string> = {
  SUPPORTED: 'Supported',
  PARTIALLY_SUPPORTED: 'Partially Supported',
  UNSUPPORTED: 'Unsupported',
  CONTRADICTED: 'Contradicted',
};

export const VERDICT_COLORS: Record<string, string> = {
  SUPPORTED: '#27AE60',
  PARTIALLY_SUPPORTED: '#D35400',
  UNSUPPORTED: '#E74C3C',
  CONTRADICTED: '#7B241C',
};

export const STANCE_DISCLAIMER = 
  "Stance reflects the orientation of comments toward the subject matter, not political affiliation or personal identity.";

export const LAYER3_DISCLAIMER =
  "Sub-issue classification (formerly Layer 3) was permanently removed from this research project. Active classification pipeline comprises Layer 1 → Layer 2 + Layer 4.";
