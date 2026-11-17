import { describe, it, expect } from 'vitest';
import { validateOfficialUrl } from './urlValidator';

describe('validateOfficialUrl', () => {
  it('validates canonical ICC domain links', () => {
    const res = validateOfficialUrl('https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions');
    expect(res.isValid).toBe(true);
    expect(res.domain).toBe('www.icc-cricket.com');
  });

  it('validates canonical Lord\'s MCC domain links', () => {
    const res = validateOfficialUrl('https://www.lords.org/mcc/the-laws-of-cricket');
    expect(res.isValid).toBe(true);
    expect(res.domain).toBe('www.lords.org');
  });

  it('validates ICC resources subdomain', () => {
    const res = validateOfficialUrl('https://resources.pulse.icc-cricket.com/ICC/document/2026/test-pc.pdf');
    expect(res.isValid).toBe(true);
  });

  it('rejects untrusted third-party domains', () => {
    const res = validateOfficialUrl('https://espncricinfo.com/rules');
    expect(res.isValid).toBe(false);
  });

  it('rejects deceptive hostnames containing trusted names', () => {
    const res = validateOfficialUrl('https://icc-cricket.com.attacker.org/steal');
    expect(res.isValid).toBe(false);
  });

  it('rejects insecure http links', () => {
    const res = validateOfficialUrl('http://www.icc-cricket.com/rules');
    expect(res.isValid).toBe(false);
  });

  it('rejects javascript: and dangerous schemes', () => {
    const res = validateOfficialUrl('javascript:alert(1)');
    expect(res.isValid).toBe(false);
  });

  it('handles null, undefined, or empty inputs safely', () => {
    expect(validateOfficialUrl(null).isValid).toBe(false);
    expect(validateOfficialUrl(undefined).isValid).toBe(false);
    expect(validateOfficialUrl('').isValid).toBe(false);
  });
});
