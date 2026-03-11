import { describe, it, expect, vi, afterEach } from 'vitest';
import { getTokenExpiryMs, isTokenExpired } from '../tokenExpiry';

function makeFakeJWT(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = btoa(JSON.stringify(payload));
  const signature = 'fake-signature';
  return `${header}.${body}.${signature}`;
}

describe('getTokenExpiryMs', () => {
  it('should parse exp from JWT and return milliseconds', () => {
    const expSeconds = 1700000000;
    const token = makeFakeJWT({ exp: expSeconds, sub: 'user1' });

    expect(getTokenExpiryMs(token)).toBe(expSeconds * 1000);
  });

  it('should return null for token without exp', () => {
    const token = makeFakeJWT({ sub: 'user1' });
    expect(getTokenExpiryMs(token)).toBeNull();
  });

  it('should return null for invalid token', () => {
    expect(getTokenExpiryMs('not-a-jwt')).toBeNull();
    expect(getTokenExpiryMs('')).toBeNull();
  });
});

describe('isTokenExpired', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('should return false if token is not expired', () => {
    const futureExp = Math.floor(Date.now() / 1000) + 3600; // +1 hour
    const token = makeFakeJWT({ exp: futureExp });

    expect(isTokenExpired(token)).toBe(false);
  });

  it('should return true if token is expired', () => {
    const pastExp = Math.floor(Date.now() / 1000) - 60; // -1 minute
    const token = makeFakeJWT({ exp: pastExp });

    expect(isTokenExpired(token)).toBe(true);
  });

  it('should return true if token expires within bufferMs', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-01-01T12:00:00Z'));

    const now = Date.now();
    const expSeconds = Math.floor(now / 1000) + 30; // expires in 30s
    const token = makeFakeJWT({ exp: expSeconds });

    // Default buffer is 60s, so 30s until expiry → expired
    expect(isTokenExpired(token)).toBe(true);

    // With 10s buffer, 30s until expiry → not expired
    expect(isTokenExpired(token, 10_000)).toBe(false);
  });
});
