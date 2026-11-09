// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { describe, it, expect, vi, afterEach } from 'vitest';
import { LocalDiningClient } from '../../src/shared/dining/local/client';
import { amount } from '../../src/features/dining/local/fields';
import { d1Fr } from '../../src/shared/i18n/d1.fr';
import { d1En } from '../../src/shared/i18n/d1.en';
import { d1Ar } from '../../src/shared/i18n/d1.ar';

const scope = {
  organization_id: 10,
  restaurant_id: 200,
  branch_id: 300,
  role: 'owner',
};
const identity = {
  actor: 'owner',
  identity_provider: 'simulated-local-rs256',
  scopes: [scope],
  customer_proofs: { '300': 'synthetic-unit-assertion' },
};
const response = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
afterEach(() => vi.unstubAllGlobals());
describe('persisted D1 browser boundary', () => {
  it.each([
    ['0E-8', '0.00000000'],
    ['1E-8', '0.00000001'],
    ['12.345E+2', '1234.5'],
    ['9007199254740993.01', '9007199254740993.01'],
  ])(
    'reads exact persisted decimal %s without floating conversion',
    async (input, expected) => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue(
          response({
            source: 'postgres-local',
            capabilities: ['configure'],
            tariffs: [
              {
                id: 1,
                reference: 'exact-local',
                component: 'preparation',
                currency: 'DZD',
                unit: 'flat',
                unit_price: input,
                valid_from: '2026-11-01T00:00:00Z',
                valid_until: null,
              },
            ],
          }),
        ),
      );
      const result = await new LocalDiningClient().workspace(scope);
      expect(result.tariffs![0]!.unit_price).toBe(expected);
    },
  );
  it('has complete translation parity and no empty translations', () => {
    for (const copy of [d1En, d1Ar]) {
      expect(Object.keys(copy).sort()).toEqual(Object.keys(d1Fr).sort());
      expect(
        Object.values(copy).every((value) => value.trim().length > 0),
      ).toBe(true);
    }
  });
  it('formats large exact money without floating conversion', () => {
    expect(amount('9007199254740993.010000', 2)).toBe('9007199254740993.01');
    expect(amount('1.005')).toBe('1.005');
    expect(amount('1500.000000', 2)).toBe('1500.00');
  });
  it('sends one scoped command with the independently held proof, without retries', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(response({}))
      .mockResolvedValueOnce(response(identity))
      .mockResolvedValueOnce(
        response(
          { detail: { code: 'dining_explicit_capability_required' } },
          403,
        ),
      );
    vi.stubGlobal('fetch', fetcher);
    const client = new LocalDiningClient();
    await client.signIn('owner');
    await expect(
      client.command(scope, { operation: 'scan_deadlines' }),
    ).rejects.toMatchObject({ status: 403 });
    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(fetcher.mock.calls[2]?.[0]).toBe(
      '/local-d1/organizations/10/restaurants/200/branches/300/dining/commands',
    );
    expect(fetcher.mock.calls[2]?.[1]).toMatchObject({
      credentials: 'same-origin',
      headers: { 'X-Customer-Proof': 'synthetic-unit-assertion' },
    });
    expect(Object.values(localStorage)).not.toContain(
      'synthetic-unit-assertion',
    );
  });
  it('rejects numeric money from the server rather than silently coercing it', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        response({
          source: 'postgres-local',
          capabilities: ['service'],
          quotes: [
            {
              id: 1,
              request_id: 2,
              version: 1,
              currency: 'DZD',
              amount: 1500,
              digest: 'a',
              expires_at: '2026-11-03',
              terms: 'test',
              components: [],
            },
          ],
        }),
      ),
    );
    await expect(new LocalDiningClient().workspace(scope)).rejects.toThrow();
  });
  it('does not fall back to synthetic data after an HTTP failure', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(response({ detail: 'unavailable' }, 503));
    vi.stubGlobal('fetch', fetcher);
    await expect(
      new LocalDiningClient().workspace(scope),
    ).rejects.toMatchObject({ status: 503 });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('reads only customer-owned workspace for a customer session', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(response({}))
      .mockResolvedValueOnce(response({ ...identity, actor: 'customer' }))
      .mockResolvedValueOnce(
        response({ source: 'postgres-local', capabilities: ['customer'] }),
      );
    vi.stubGlobal('fetch', fetcher);
    const client = new LocalDiningClient();
    await client.signIn('customer');
    await client.workspace(scope);
    expect(fetcher.mock.calls[2]?.[0]).toBe(
      '/local-d1/dining/restaurants/200/branches/300/customer-workspace',
    );
  });
});
