import { describe, it, expect } from 'vitest';
import { fmtCcy, fmtNum, fmtPct } from '@/lib/format';

describe('fmtCcy', () => {
  it('formats a number as BRL currency', () => {
    const out = fmtCcy(1234.5);
    expect(out).toContain('R$');
    // Independe do tipo de espaço/separador do ICU: confere só os dígitos.
    expect(out.replace(/[^\d]/g, '')).toBe('123450');
  });

  it('returns em-dash for null/undefined', () => {
    expect(fmtCcy(undefined)).toBe('—');
  });

  it('passes through non-numeric strings', () => {
    expect(fmtCcy('N/A')).toBe('N/A');
  });

  it('stringifies non-finite numbers', () => {
    expect(fmtCcy(NaN)).toBe('NaN');
  });
});

describe('fmtNum', () => {
  it('rounds and groups thousands', () => {
    expect(fmtNum(1234.6).replace(/\D/g, '')).toBe('1235');
  });

  it('returns em-dash for undefined', () => {
    expect(fmtNum(undefined)).toBe('—');
  });
});

describe('fmtPct', () => {
  it('uses 2 decimals by default', () => {
    expect(fmtPct(12.345)).toBe('12.35%');
  });

  it('respects the decimals argument', () => {
    expect(fmtPct(12.345, 1)).toBe('12.3%');
  });

  it('returns em-dash for undefined', () => {
    expect(fmtPct(undefined)).toBe('—');
  });
});
