// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAuthenticatedAdapter } from '../../src/shared/access/operational';
import { isAuthenticatedAccess } from '../../src/shared/access/contracts';
import { LocalDiningClient } from '../../src/shared/dining/local/client';

afterEach(() => vi.unstubAllGlobals());
const identity = {
  issuer: 'https://identity.example.invalid/realms/moulai-staging',
  subject: 'fictitious-user',
  displayName: { fr: 'Recette', en: 'Test', ar: 'اختبار' },
  area: 'tenant',
  source: 'authenticated-staging',
  expiresAt: 2000000000,
  platformPermissions: [],
};

describe('staging admission without simulated authentication', () => {
  it('requires the staging source returned by the server', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify(identity), { status: 200 }),
      );
    vi.stubGlobal('fetch', fetch);
    const adapter = createAuthenticatedAdapter('authenticated-staging');
    expect(
      (await adapter.getSession(new AbortController().signal))?.source,
    ).toBe('authenticated-staging');
    expect(isAuthenticatedAccess(adapter.mode)).toBe(true);
    expect(fetch.mock.calls[0]?.[0]).toBe('/api/web/session');
  });
  it.each(['synthetic', 'authenticated-local'])(
    'refuses a foreign %s session projection',
    async (source) => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue(
          new Response(JSON.stringify({ ...identity, source }), {
            status: 200,
          }),
        ),
      );
      await expect(
        createAuthenticatedAdapter('authenticated-staging').getSession(
          new AbortController().signal,
        ),
      ).rejects.toThrow();
    },
  );
  it('has no role-selector login or implicit retry', async () => {
    const fetch = vi.fn();
    vi.stubGlobal('fetch', fetch);
    await expect(
      createAuthenticatedAdapter('authenticated-staging').openReview('admin'),
    ).rejects.toThrow();
    expect(fetch).not.toHaveBeenCalled();
  });
  it('preserves legacy local route mapping while authenticated mode uses canonical API paths', () => {
    expect(new LocalDiningClient(false).url('/api/web/dining-session')).toBe(
      '/local-d1/session',
    );
    expect(new LocalDiningClient(true).url('/api/web/dining/public/menu')).toBe(
      '/api/web/dining/public/menu',
    );
  });
});
