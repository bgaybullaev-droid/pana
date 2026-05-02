import { describe, it, expect } from 'vitest';

/**
 * Extracted logic from SellerListingsPage — mirrors the getListingSource function.
 * Tests case-insensitive source_type matching (DB stores UPPERCASE enums).
 */
function getListingSource(sourceType?: string | null): 'platform' | 'olx' {
  if (sourceType?.toUpperCase() === 'CLAIMED') return 'olx';
  return 'platform';
}

describe('getListingSource', () => {
  it('CLAIMED (uppercase from DB) → olx', () => {
    expect(getListingSource('CLAIMED')).toBe('olx');
  });

  it('claimed (lowercase) → olx', () => {
    expect(getListingSource('claimed')).toBe('olx');
  });

  it('Claimed (mixed case) → olx', () => {
    expect(getListingSource('Claimed')).toBe('olx');
  });

  it('MANUAL → platform', () => {
    expect(getListingSource('MANUAL')).toBe('platform');
  });

  it('manual → platform', () => {
    expect(getListingSource('manual')).toBe('platform');
  });

  it('PARSED → platform', () => {
    expect(getListingSource('PARSED')).toBe('platform');
  });

  it('null → platform', () => {
    expect(getListingSource(null)).toBe('platform');
  });

  it('undefined → platform', () => {
    expect(getListingSource(undefined)).toBe('platform');
  });

  it('empty string → platform', () => {
    expect(getListingSource('')).toBe('platform');
  });
});
