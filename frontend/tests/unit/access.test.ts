// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it, vi } from 'vitest';
import { createSyntheticAdapter } from '../../src/review/syntheticAdapter';
import { disconnectedAdapter } from '../../src/shared/access/disconnected';
import { createAccessAdapter } from '../../src/shared/access/runtime';
import type { ReviewProfile } from '../../src/shared/access/contracts';
import { fr } from '../../src/shared/i18n/fr';
import { ar } from '../../src/shared/i18n/ar';

/** Create fresh, deliberately synthetic state for each browser-adapter test. */
async function adapterFor(profile: ReviewProfile) {
  const adapter = createSyntheticAdapter(0);
  await adapter.openReview(profile);
  return adapter;
}
const signal = (): AbortSignal => new AbortController().signal;

describe('isolated review adapter', () => {
  it('keeps a common owner’s A/B restaurant sets separate', async () => {
    const adapter = await adapterFor('owner');
    expect(
      (await adapter.organizations(signal())).map((row) => row.id),
    ).toEqual([9101, 9102]);
    expect(
      (await adapter.restaurants(9101, signal())).map((row) => row.id),
    ).toEqual([9201, 9202]);
    expect(
      (await adapter.restaurants(9102, signal())).map((row) => row.id),
    ).toEqual([9203]);
    await expect(
      adapter.restaurant(9101, 9203, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
  });

  it('limits staff to explicit restaurant grants', async () => {
    const adapter = await adapterFor('employee');
    expect(
      (await adapter.restaurants(9101, signal())).map((row) => row.id),
    ).toEqual([9202]);
    await expect(
      adapter.restaurant(9101, 9201, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
  });

  it('gives empty grants no restaurant and never falls back to a common owner', async () => {
    const adapter = await adapterFor('empty');
    expect(await adapter.restaurants(9101, signal())).toEqual([]);
    await expect(
      adapter.restaurant(9101, 9201, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
  });

  it('rejects company switching beyond the manager membership', async () => {
    const adapter = await adapterFor('manager');
    expect(
      (await adapter.restaurants(9101, signal())).map((row) => row.id),
    ).toEqual([9201]);
    await expect(
      adapter.restaurant(9101, 9202, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
    await expect(adapter.restaurants(9102, signal())).rejects.toMatchObject({
      code: 'notFound',
    });
  });

  it.each(['unlinked', 'suspended', 'error'] as const)(
    'renders the %s outcome without granting access',
    async (profile) => {
      const adapter = await adapterFor(profile);
      await expect(adapter.organizations(signal())).rejects.toMatchObject({
        code: profile === 'error' ? 'temporary' : profile,
      });
    },
  );

  it('keeps platform access independent of tenant membership', async () => {
    const adapter = await adapterFor('admin');
    expect((await adapter.getSession(signal()))?.area).toBe('platform');
    await expect(adapter.organizations(signal())).rejects.toMatchObject({
      code: 'noAccess',
    });
  });

  it.each(['owner', 'manager', 'employee'] as const)(
    'matches the approved E1 %s permissions without fulfillment or platform powers',
    async (profile) => {
      const schema = readFileSync(
        resolve('../migration_support/tenant_e1_schema.py'),
        'utf8',
      );
      const block = new RegExp(`"${profile}": \\(([\\s\\S]*?)\\),`).exec(
        schema,
      )?.[1];
      expect(block).toBeDefined();
      const approved = [...(block ?? '').matchAll(/"(tenant\.[a-z.]+)"/g)].map(
        (match) => match[1],
      );
      const companies = await (
        await adapterFor(profile)
      ).organizations(signal());
      expect(companies[0]?.permissions).toEqual(approved);
      expect(companies[0]?.permissions).not.toContain('tenant.orders.fulfill');
      expect(
        companies[0]?.permissions.some(
          (permission) => !permission.startsWith('tenant.'),
        ),
      ).toBe(false);
    },
  );

  it('clears identity state on sign-out and rejects a cancelled read', async () => {
    const adapter = await adapterFor('owner');
    const controller = new AbortController();
    controller.abort();
    await expect(
      adapter.restaurants(9101, controller.signal),
    ).rejects.toMatchObject({ name: 'AbortError' });
    await adapter.signOut();
    expect(await adapter.getSession(signal())).toBeNull();
    await expect(adapter.organizations(signal())).rejects.toMatchObject({
      code: 'noAccess',
    });
  });
});

describe('unconnected default', () => {
  it('never silently chooses synthetic data or calls a remote API', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    expect(await createAccessAdapter()).toBe(disconnectedAdapter);
    expect(await disconnectedAdapter.getSession(signal())).toBeNull();
    await expect(disconnectedAdapter.openReview('owner')).rejects.toMatchObject(
      { code: 'notConnected' },
    );
    await expect(
      disconnectedAdapter.restaurants(9101, signal()),
    ).rejects.toMatchObject({ code: 'notConnected' });
    expect(fetch).not.toHaveBeenCalled();
  });
  it('maintains all French keys in Arabic, including Arabic plural forms', () => {
    expect(Object.keys(fr).every((key) => key in ar)).toBe(true);
    for (const plural of ['zero', 'one', 'two', 'few', 'many', 'other'])
      expect(ar[`restaurants.count_${plural}`]).toBeTruthy();
  });
});
