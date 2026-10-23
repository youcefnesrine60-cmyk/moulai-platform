// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { createSyntheticAdapter } from '../../src/review/syntheticAdapter';
import { createManagementAdapter } from '../../src/review/managementAdapter';
import {
  AccessError,
  type ReviewProfile,
} from '../../src/shared/access/contracts';
import { disconnectedAdapter } from '../../src/shared/access/disconnected';
import {
  ReviewConflict,
  lockedOrderStatuses,
  type ReviewCommand,
} from '../../src/shared/business/contracts';
import {
  parsePrice,
  profileSchema,
  productSchema,
  optionSchema,
} from '../../src/shared/business/validation';
import { businessFr } from '../../src/shared/i18n/business.fr';
import { businessAr } from '../../src/shared/i18n/business.ar';

const scopeA = { organizationId: 9101, restaurantId: 9201 };
const scopeB = { organizationId: 9102, restaurantId: 9203 };
const signal = (): AbortSignal => new AbortController().signal;

/** Every case starts with a new ephemeral session; no shared fixture mutations. */
async function owner(profile: ReviewProfile = 'owner') {
  const adapter = createSyntheticAdapter(0);
  await adapter.openReview(profile);
  return adapter;
}

describe('money and existing-schema validation', () => {
  it('matches backend locked states and price ceilings without importing Python', () => {
    const constants = readFileSync(
      '../app/services/business/orders/constants.py',
      'utf8',
    );
    const block =
      /LOCKED_STATUSES:\s*Set\[str\]\s*=\s*\{([\s\S]*?)\}/.exec(
        constants,
      )?.[1] ?? '';
    expect(
      [...block.matchAll(/"([a-z_]+)"/g)].map((match) => match[1]).sort(),
    ).toEqual([...lockedOrderStatuses].sort());
    expect(
      readFileSync('../app/services/business/product_service.py', 'utf8'),
    ).toMatch(/MAX_PRODUCT_PRICE = 10000000\.0/);
    expect(
      readFileSync(
        '../app/services/business/product_option_service.py',
        'utf8',
      ),
    ).toMatch(/MAX_EXTRA_PRICE = 1000000\.0/);
    const value = {
      categoryId: 1,
      name: 'Review',
      description: '',
      price: 1000000000,
      available: true,
      sortOrder: 0,
    };
    expect(productSchema.safeParse(value).success).toBe(true);
    expect(
      productSchema.safeParse({ ...value, price: value.price + 1 }).success,
    ).toBe(false);
    const extra = {
      groupId: 1,
      name: 'Review',
      extraPrice: 100000000,
      available: true,
      sortOrder: 0,
    };
    expect(optionSchema.safeParse(extra).success).toBe(true);
    expect(
      optionSchema.safeParse({ ...extra, extraPrice: extra.extraPrice + 1 })
        .success,
    ).toBe(false);
  });
  it.each([
    '',
    '-1',
    '0',
    '0.00',
    'NaN',
    'Infinity',
    '1e3',
    '1.234',
    '1,2.3',
    '9999999999',
    '1 000',
    '.5',
  ])('rejects invalid product price %s', (value) => {
    expect(parsePrice(value)).toBeNull();
  });
  it.each([
    ['9,50', 950],
    ['950', 95000],
    ['0.01', 1],
    [' 12.5 ', 1250],
  ] as const)('parses DZD %s into exact centimes', (value, expected) => {
    expect(parsePrice(value)).toBe(expected);
  });
  it('allows free options without allowing free products', () => {
    expect(parsePrice('0.00', true)).toBe(0);
    expect(parsePrice('0.00')).toBeNull();
  });
  it('rejects identity/ownership fields instead of silently accepting them', () => {
    expect(
      profileSchema.safeParse({
        name: 'Review',
        phone: '+213555000000',
        type: 'restaurant',
        wilaya: 'Alger',
        owner_id: 1,
      }).success,
    ).toBe(false);
  });
  it('keeps complete French/Arabic business catalogs', () => {
    expect(Object.keys(businessAr).sort()).toEqual(
      Object.keys(businessFr).sort(),
    );
    expect(
      Object.values(businessAr).every((value) => /[\u0600-\u06ff]/.test(value)),
    ).toBe(true);
  });
});

describe('scoped synthetic management boundary', () => {
  it('preserves A/B catalogue and order separation for the same owner', async () => {
    const adapter = await owner();
    const a = await adapter.workspace(scopeA, signal());
    const b = await adapter.workspace(scopeB, signal());
    expect(a.products[0]?.name).not.toEqual(b.products[0]?.name);
    expect(a.orders.every((row) => row.number.includes('9201'))).toBe(true);
    expect(b.orders.every((row) => row.number.includes('9203'))).toBe(true);
    await expect(
      adapter.workspace({ ...scopeA, restaurantId: 9203 }, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
    await adapter.saveReview(
      scopeA,
      a.reviewRevision,
      { kind: 'category', id: null, value: { name: 'Only A', sortOrder: 2 } },
      signal(),
    );
    expect(
      (await adapter.workspace(scopeB, signal())).categories.some(
        (row) => row.name === 'Only A',
      ),
    ).toBe(false);
  });
  it.each([
    'manager',
    'employee',
    'empty',
    'admin',
    'unlinked',
    'suspended',
  ] as const)(
    'denies company B to %s even on direct adapter access',
    async (profile) => {
      const adapter = await owner(profile);
      await expect(adapter.workspace(scopeB, signal())).rejects.toBeInstanceOf(
        AccessError,
      );
      await expect(
        adapter.saveReview(
          scopeB,
          1,
          {
            kind: 'category',
            id: null,
            value: { name: 'Forbidden', sortOrder: 0 },
          },
          signal(),
        ),
      ).rejects.toBeInstanceOf(AccessError);
    },
  );
  it('checks staff grants and refuses every management command', async () => {
    const adapter = await owner('employee');
    const scope = { ...scopeA, restaurantId: 9202 };
    const state = await adapter.workspace(scope, signal());
    const commands: ReviewCommand[] = [
      { kind: 'profile', value: state.profile },
      {
        kind: 'category',
        id: null,
        value: { name: 'Forbidden', sortOrder: 0 },
      },
      {
        kind: 'product',
        id: null,
        value: {
          categoryId: 920201,
          name: 'Forbidden',
          description: '',
          price: 100,
          available: true,
          sortOrder: 0,
        },
      },
      {
        kind: 'group',
        id: null,
        value: {
          productId: 920210,
          name: 'Forbidden',
          required: false,
          multipleChoice: false,
          sortOrder: 0,
        },
      },
      {
        kind: 'option',
        id: null,
        value: {
          groupId: 920220,
          name: 'Forbidden',
          extraPrice: 0,
          available: true,
          sortOrder: 0,
        },
      },
      { kind: 'orderNote', id: 920260, note: 'Forbidden' },
    ];
    for (const command of commands)
      await expect(
        adapter.saveReview(scope, 1, command, signal()),
      ).rejects.toMatchObject({ code: 'noAccess' });
    expect(await adapter.workspace(scope, signal())).toEqual(state);
    await expect(adapter.workspace(scopeA, signal())).rejects.toMatchObject({
      code: 'notFound',
    });
  });
  it('allows a manager to edit only their explicitly granted restaurant', async () => {
    const adapter = await owner('manager');
    const state = await adapter.workspace(scopeA, signal());
    await adapter.saveReview(
      scopeA,
      1,
      { kind: 'profile', value: { ...state.profile, name: 'Review rename' } },
      signal(),
    );
    expect((await adapter.restaurant(9101, 9201, signal())).name.fr).toBe(
      'Review rename',
    );
    await expect(
      adapter.saveReview(
        { ...scopeA, restaurantId: 9202 },
        1,
        { kind: 'profile', value: state.profile },
        signal(),
      ),
    ).rejects.toMatchObject({ code: 'notFound' });
  });
  it('denies a missing permission even when a restaurant is selected', async () => {
    const adapter = createManagementAdapter(
      (_scope, permission) => {
        if (permission === 'tenant.catalog.manage')
          throw new AccessError('noAccess');
      },
      async (request) => request.throwIfAborted(),
    );
    await expect(
      adapter.saveReview(
        scopeA,
        1,
        { kind: 'category', id: null, value: { name: 'Denied', sortOrder: 0 } },
        signal(),
      ),
    ).rejects.toMatchObject({ code: 'noAccess' });
  });
  it('rejects references to another restaurant’s categories, products, groups and orders atomically', async () => {
    const adapter = await owner();
    const before = await adapter.workspace(scopeA, signal());
    const b = await adapter.workspace(scopeB, signal());
    const product = before.products[0]!;
    const commands: ReviewCommand[] = [
      {
        kind: 'product',
        id: product.id,
        value: {
          categoryId: b.categories[0]!.id,
          name: 'Cross',
          description: '',
          price: 100,
          available: true,
          sortOrder: 0,
        },
      },
      {
        kind: 'category',
        id: b.categories[0]!.id,
        value: { name: 'Cross', sortOrder: 0 },
      },
      {
        kind: 'group',
        id: null,
        value: {
          productId: b.products[0]!.id,
          name: 'Cross',
          required: false,
          multipleChoice: false,
          sortOrder: 0,
        },
      },
      {
        kind: 'option',
        id: null,
        value: {
          groupId: b.groups[0]!.id,
          name: 'Cross',
          extraPrice: 0,
          available: true,
          sortOrder: 0,
        },
      },
      { kind: 'orderNote', id: b.orders[0]!.id, note: 'Cross' },
    ];
    for (const command of commands)
      await expect(
        adapter.saveReview(scopeA, 1, command, signal()),
      ).rejects.toMatchObject({ code: 'notFound' });
    expect(await adapter.workspace(scopeA, signal())).toEqual(before);
  });
  it('creates and edits each catalogue level, including zero-priced options and availability', async () => {
    const adapter = await owner();
    await adapter.saveReview(
      scopeA,
      1,
      {
        kind: 'category',
        id: null,
        value: { name: 'Review category', sortOrder: 2 },
      },
      signal(),
    );
    let state = await adapter.workspace(scopeA, signal());
    const category = state.categories.find(
      (row) => row.name === 'Review category',
    )!;
    await adapter.saveReview(
      scopeA,
      2,
      {
        kind: 'product',
        id: null,
        value: {
          categoryId: category.id,
          name: 'Review product',
          description: 'Description',
          price: 12345,
          available: true,
          sortOrder: 0,
        },
      },
      signal(),
    );
    state = await adapter.workspace(scopeA, signal());
    const product = state.products.find(
      (row) => row.name === 'Review product',
    )!;
    await adapter.saveReview(
      scopeA,
      3,
      {
        kind: 'group',
        id: null,
        value: {
          productId: product.id,
          name: 'Review group',
          required: true,
          multipleChoice: false,
          sortOrder: 0,
        },
      },
      signal(),
    );
    state = await adapter.workspace(scopeA, signal());
    const group = state.groups.find((row) => row.name === 'Review group')!;
    await adapter.saveReview(
      scopeA,
      4,
      {
        kind: 'option',
        id: null,
        value: {
          groupId: group.id,
          name: 'Free choice',
          extraPrice: 0,
          available: true,
          sortOrder: 0,
        },
      },
      signal(),
    );
    state = await adapter.workspace(scopeA, signal());
    const option = state.options.find((row) => row.name === 'Free choice')!;
    const { id: _id, ...value } = option;
    await adapter.saveReview(
      scopeA,
      5,
      { kind: 'option', id: option.id, value: { ...value, available: false } },
      signal(),
    );
    expect(
      (await adapter.workspace(scopeA, signal())).options.find(
        (row) => row.id === option.id,
      )?.available,
    ).toBe(false);
  });
  it('rejects stale concurrent edits without overwriting the accepted change', async () => {
    const adapter = await owner();
    const results = await Promise.allSettled(
      ['First', 'Second'].map((name) =>
        adapter.saveReview(
          scopeA,
          1,
          { kind: 'category', id: null, value: { name, sortOrder: 0 } },
          signal(),
        ),
      ),
    );
    expect(results.filter((row) => row.status === 'fulfilled')).toHaveLength(1);
    const rejected = results.find((row) => row.status === 'rejected');
    expect(rejected?.status === 'rejected' && rejected.reason).toBeInstanceOf(
      ReviewConflict,
    );
    expect((await adapter.workspace(scopeA, signal())).reviewRevision).toBe(2);
  });
  it('prevents mutations after sign-out and does not carry edits into the next session', async () => {
    const adapter = createSyntheticAdapter(15);
    await adapter.openReview('owner');
    const pending = adapter.saveReview(
      scopeA,
      1,
      {
        kind: 'category',
        id: null,
        value: { name: 'Late change', sortOrder: 0 },
      },
      signal(),
    );
    const refusal = expect(pending).rejects.toMatchObject({ code: 'noAccess' });
    await adapter.signOut();
    await adapter.openReview('owner');
    await refusal;
    const state = await adapter.workspace(scopeA, signal());
    expect(state.categories.some((row) => row.name === 'Late change')).toBe(
      false,
    );
    expect(state.reviewRevision).toBe(1);
  });
  it('cancels pending changes without applying them', async () => {
    const adapter = createSyntheticAdapter(15);
    await adapter.openReview('owner');
    const controller = new AbortController();
    const pending = adapter.saveReview(
      scopeA,
      1,
      {
        kind: 'category',
        id: null,
        value: { name: 'Cancelled', sortOrder: 0 },
      },
      controller.signal,
    );
    const refusal = expect(pending).rejects.toMatchObject({
      name: 'AbortError',
    });
    controller.abort();
    await refusal;
    expect((await adapter.workspace(scopeA, signal())).reviewRevision).toBe(1);
  });
  it('changes notes without altering amounts, payments, items or status', async () => {
    const adapter = await owner();
    const before = await adapter.workspace(scopeA, signal());
    const order = before.orders[0]!;
    await adapter.saveReview(
      scopeA,
      1,
      { kind: 'orderNote', id: order.id, note: 'Review note' },
      signal(),
    );
    const changed = (await adapter.workspace(scopeA, signal())).orders[0];
    expect(changed).toEqual({ ...order, customerNote: 'Review note' });
  });
  it('keeps invalid updates atomic and snapshots detached from internal state', async () => {
    const adapter = await owner();
    const before = await adapter.workspace(scopeA, signal());
    await expect(
      adapter.saveReview(
        scopeA,
        1,
        {
          kind: 'product',
          id: null,
          value: {
            categoryId: before.categories[0]!.id,
            name: 'Invalid',
            description: '',
            price: -100,
            available: true,
            sortOrder: 0,
          },
        },
        signal(),
      ),
    ).rejects.toThrow();
    expect(await adapter.workspace(scopeA, signal())).toEqual(before);
    Reflect.set(before.products[0]!, 'name', 'Attempted external mutation');
    expect(
      (await adapter.workspace(scopeA, signal())).products[0]?.name,
    ).not.toBe('Attempted external mutation');
  });
  it('keeps normal-mode reads and writes disconnected', async () => {
    await expect(
      disconnectedAdapter.workspace(scopeA, signal()),
    ).rejects.toMatchObject({ code: 'notConnected' });
    await expect(
      disconnectedAdapter.saveReview(
        scopeA,
        1,
        { kind: 'category', id: null, value: { name: 'No', sortOrder: 0 } },
        signal(),
      ),
    ).rejects.toMatchObject({ code: 'notConnected' });
  });
  it.each(['delivering', 'delivered', 'completed', 'cancelled'] as const)(
    'refuses note updates for locked status %s',
    async (status) => {
      const adapter = await owner();
      const before = await adapter.workspace(scopeA, signal());
      const order = before.orders.find((row) => row.status === status)!;
      await expect(
        adapter.saveReview(
          scopeA,
          1,
          { kind: 'orderNote', id: order.id, note: 'Blocked' },
          signal(),
        ),
      ).rejects.toMatchObject({ code: 'noAccess' });
      expect(await adapter.workspace(scopeA, signal())).toEqual(before);
    },
  );
});
