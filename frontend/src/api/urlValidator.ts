/**
 * Official URL Validator for CricketIQ Citations.
 * Validates that links to official rulebooks point exclusively to trusted
 * governing authority domains (ICC and MCC / Lord's) over secure HTTPS.
 */

const TRUSTED_DOMAINS = [
  'icc-cricket.com',
  'www.icc-cricket.com',
  'resources.pulse.icc-cricket.com',
  'lords.org',
  'www.lords.org',
];

export interface ValidatedUrl {
  isValid: boolean;
  sanitizedUrl: string | null;
  domain: string | null;
}

export function validateOfficialUrl(rawUrl: string | null | undefined): ValidatedUrl {
  if (!rawUrl || typeof rawUrl !== 'string') {
    return { isValid: false, sanitizedUrl: null, domain: null };
  }

  const trimmed = rawUrl.trim();

  try {
    const parsed = new URL(trimmed);

    // Strictly enforce HTTPS
    if (parsed.protocol !== 'https:') {
      return { isValid: false, sanitizedUrl: null, domain: null };
    }

    const hostname = parsed.hostname.toLowerCase();

    // Verify hostname against trusted official authority domains
    const isTrusted = TRUSTED_DOMAINS.some(
      (trusted) => hostname === trusted || hostname.endsWith(`.${trusted}`)
    );

    if (!isTrusted) {
      return { isValid: false, sanitizedUrl: null, domain: hostname };
    }

    return {
      isValid: true,
      sanitizedUrl: parsed.toString(),
      domain: hostname,
    };
  } catch {
    return { isValid: false, sanitizedUrl: null, domain: null };
  }
}
