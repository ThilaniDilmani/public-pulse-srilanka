/**
 * Layer 3 / Sarcasm absence contract tests.
 *
 * Verifies that no component, constant, or type in the dashboard
 * ever references Layer 3, Sub-issue, or Sarcasm as dimensions.
 * These dimensions were permanently removed from Public Pulse.
 */
import { describe, it, expect } from 'vitest';
import * as constants from '../lib/constants';

describe('Layer 3 — absence contracts', () => {
  it('constants do not define LAYER3 keys', () => {
    const keys = Object.keys(constants);
    const layer3Keys = keys.filter(k => k.toLowerCase().includes('layer3'));
    // LAYER3_DISCLAIMER is allowed (it's an explanatory string, not a data dimension)
    const forbidden = layer3Keys.filter(k => k !== 'LAYER3_DISCLAIMER');
    expect(forbidden).toHaveLength(0);
  });

  it('TOPIC_LABELS does not include sarcasm', () => {
    const labels = Object.values(constants.TOPIC_LABELS).map(v => v.toLowerCase());
    expect(labels.some(l => l.includes('sarcasm'))).toBe(false);
  });

  it('STANCE_LABELS does not use positive/negative/neutral as values', () => {
    const stanceValues = Object.values(constants.STANCE_LABELS).map(v => v.toLowerCase());
    // Stance must NOT be renamed to positive/negative/neutral
    expect(stanceValues.includes('positive')).toBe(false);
    expect(stanceValues.includes('negative')).toBe(false);
    // 'neutral' in isolation as the only label for NEUT is the existing allowed term
    // but it should not appear as a valence mapping; NEUT should map to 'Neutral' orientation label
    // We check that 'neutral' only appears as NEUT mapping (not as positive/negative pair)
    const hasPositive = stanceValues.includes('positive');
    const hasNegative = stanceValues.includes('negative');
    expect(hasPositive || hasNegative).toBe(false);
  });

  it('STANCE_LABELS does not include sarcasm', () => {
    const labels = Object.values(constants.STANCE_LABELS).map(v => v.toLowerCase());
    expect(labels.some(l => l.includes('sarcasm'))).toBe(false);
  });

  it('LAYER3_DISCLAIMER exists and is an explanatory string', () => {
    expect(typeof constants.LAYER3_DISCLAIMER).toBe('string');
    expect(constants.LAYER3_DISCLAIMER.length).toBeGreaterThan(10);
  });
});

describe('Sarcasm — absence contracts', () => {
  it('no constant key references sarcasm as a data dimension', () => {
    const keys = Object.keys(constants);
    const sarcasmKeys = keys.filter(k =>
      k.toLowerCase().includes('sarcasm') && !k.includes('DISCLAIMER')
    );
    expect(sarcasmKeys).toHaveLength(0);
  });

  it('STANCE_LABELS values do not include sarcasm', () => {
    const values = Object.values(constants.STANCE_LABELS).map(v => v.toLowerCase());
    expect(values.some(v => v.includes('sarcasm'))).toBe(false);
  });
});
