// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// MoulAI™ — HTTP adapter boundaries; provider/browser proofs are tested separately.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { operationalAdapter } from '../../src/shared/access/operational';
import { procedure } from '../../src/shared/dining/help/documentation';
import { redactLocalMessage } from '../../src/shared/access/logSafety';
import { PublicDiningClient } from '../../src/shared/dining/local/publicClient';
import { LocalDiningClient } from '../../src/shared/dining/local/client';
import {
  campaignDateInput,
  campaignDateValue,
} from '../../src/features/integration/campaignDates';

afterEach(() => vi.unstubAllGlobals());
describe('authenticated local adapter', () => {
  it('redacts credential headers in browser API diagnostics', () => {
    const message = redactLocalMessage(
      ' - Cookie: __Secure-moulai-session=offline-fixture-secret\n - Authorization: Bearer offline-fixture-token\n - Set-Cookie: another=offline-fixture-cookie',
    );
    expect(message).not.toContain('offline-fixture');
    expect(message).toContain('Cookie: [REDACTED]');
    expect(message).toContain('Authorization: [REDACTED]');
  });
  it('uses explicit UTC dates and preserves an unchanged precise persisted instant', () => {
    expect(campaignDateValue('2027-03-28T02:30', null)).toBe(
      '2027-03-28T02:30:00.000Z',
    );
    const precise = '2027-10-31T02:30:01.123456+00:00';
    expect(campaignDateValue(campaignDateInput(precise), precise)).toBe(
      precise,
    );
    expect(() => campaignDateValue('2027-02-30T12:00', null)).toThrow();
  });
  it('routes public verification through the integrated origin without creating a staff session', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ status: 'invalid' })));
    vi.stubGlobal('fetch', fetcher);
    expect(
      await new PublicDiningClient(new LocalDiningClient(true)).verify(
        'A'.repeat(43),
      ),
    ).toEqual({ status: 'invalid' });
    expect(fetcher).toHaveBeenCalledWith(
      '/api/web/dining/public/verify',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('redacts callback parameters and bearer tokens from local failure diagnostics', () => {
    const message = redactLocalMessage(
      'proxy /api/web/auth/callback?state=PRIVATESTATE&code=PRIVATEAUTHCODE Bearer PRIVATEBEARER',
    );
    expect(message).not.toContain('PRIVATESTATE');
    expect(message).not.toContain('PRIVATEAUTHCODE');
    expect(message).not.toContain('PRIVATEBEARER');
    expect(message).toContain('/api/web/auth/callback');
  });
  it('reads a real session projection without a role selector or token storage', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          issuer: 'https://127.0.0.1:8444/realms/moulai-local',
          subject: 'persisted-subject',
          displayName: { fr: 'Compte', en: 'Account', ar: 'حساب' },
          area: 'tenant',
          source: 'authenticated-local',
          expiresAt: 1900000000,
          platformPermissions: [],
        }),
      ),
    );
    vi.stubGlobal('fetch', fetcher);
    expect(
      (await operationalAdapter.getSession(new AbortController().signal))
        ?.subject,
    ).toBe('persisted-subject');
    expect(fetcher).toHaveBeenCalledWith(
      '/api/web/session',
      expect.objectContaining({
        credentials: 'same-origin',
        cache: 'no-store',
      }),
    );
  });
  it('refuses an unauthorized API projection instead of substituting fixture data', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Tenant access denied' }), {
          status: 403,
        }),
      ),
    );
    await expect(
      operationalAdapter.restaurants(99, new AbortController().signal),
    ).rejects.toMatchObject({
      code: 'noAccess',
    });
  });
  it('preserves an absent association as an empty collection', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('[]')));
    expect(
      await operationalAdapter.organizations(new AbortController().signal),
    ).toEqual([]);
  });
  it('cannot issue a fictional local review identity', async () => {
    await expect(operationalAdapter.openReview('owner')).rejects.toBeDefined();
  });
  it('keeps rehearsal instructions out of the real sign-in guide', () => {
    for (const locale of ['fr', 'en', 'ar'] as const) {
      const actual = procedure('start', true).copy[locale];
      expect(actual.steps[0]).toContain('/access');
      expect(actual.steps).not.toEqual(procedure('start').copy[locale].steps);
    }
  });
});
