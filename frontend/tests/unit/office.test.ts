import { describe, expect, it } from 'vitest';
import { createSyntheticAdapter } from '../../src/review/syntheticAdapter';
import { disconnectedAdapter } from '../../src/shared/access/disconnected';
import { receiptDraftSchema } from '../../src/shared/office/validation';
import { officeFr } from '../../src/shared/i18n/office.fr';
import { officeEn } from '../../src/shared/i18n/office.en';
import { officeAr } from '../../src/shared/i18n/office.ar';

const scope = { organizationId: 9101, restaurantId: 9201 };
const signal = () => new AbortController().signal;

describe('reports, billing and platform review boundaries', () => {
  it('rejects a restaurant paired with the wrong company even for an owner of both', async () => {
    const adapter = createSyntheticAdapter(0);
    await adapter.openReview('owner');
    const wrongPair = { organizationId: 9101, restaurantId: 9203 };
    await expect(adapter.payments(wrongPair, signal())).rejects.toMatchObject({
      code: 'notFound',
    });
    await expect(adapter.report(wrongPair, signal())).rejects.toMatchObject({
      code: 'notFound',
    });
  });
  it('denies a delayed platform read after the session is closed', async () => {
    const adapter = createSyntheticAdapter(25);
    await adapter.openReview('admin');
    const pending = adapter.platformRecords('receipts', signal());
    const checked = expect(pending).rejects.toMatchObject({ code: 'noAccess' });
    await adapter.signOut();
    await checked;
  });
  for (const profile of ['owner', 'manager'] as const)
    it(`${profile} reads counts from the selected restaurant catalogue`, async () => {
      const adapter = createSyntheticAdapter(0);
      await adapter.openReview(profile);
      const data = await adapter.workspace(scope, signal());
      expect(await adapter.report(scope, signal())).toEqual({
        restaurantId: 9201,
        totalOrders: data.orders.length,
        totalProducts: data.products.length,
        totalCategories: data.categories.length,
        averageOrderValue: null,
        monthlyGrowth: null,
      });
    });
  it('keeps restaurant payments separate, returns defensive copies and has no write operation', async () => {
    const adapter = createSyntheticAdapter(0);
    await adapter.openReview('owner');
    const first = await adapter.payments(scope, signal());
    const other = await adapter.payments(
      { organizationId: 9102, restaurantId: 9203 },
      signal(),
    );
    expect(first.every((p) => p.restaurantId === 9201)).toBe(true);
    expect(other.every((p) => p.restaurantId === 9203)).toBe(true);
    expect(
      first.map((p) => p.id).some((id) => other.some((p) => p.id === id)),
    ).toBe(false);
    expect(first).not.toBe(await adapter.payments(scope, signal()));
    expect('submitReceipt' in adapter).toBe(false);
    await expect(
      adapter.platformRecords('receipts', signal()),
    ).rejects.toMatchObject({ code: 'noAccess' });
  });
  it('manager cannot read billing, even with valid restaurant access', async () => {
    const adapter = createSyntheticAdapter(0);
    await adapter.openReview('manager');
    await expect(adapter.payments(scope, signal())).rejects.toMatchObject({
      code: 'noAccess',
    });
    await expect(
      adapter.report({ organizationId: 9101, restaurantId: 9202 }, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
    await expect(
      adapter.report({ organizationId: 9102, restaurantId: 9203 }, signal()),
    ).rejects.toMatchObject({ code: 'notFound' });
  });
  it('staff cannot obtain financial/report data despite its granted restaurant', async () => {
    const adapter = createSyntheticAdapter(0);
    await adapter.openReview('employee');
    const granted = { organizationId: 9101, restaurantId: 9202 };
    await expect(adapter.report(granted, signal())).rejects.toMatchObject({
      code: 'noAccess',
    });
    await expect(adapter.payments(granted, signal())).rejects.toMatchObject({
      code: 'noAccess',
    });
  });
  for (const section of ['requests', 'receipts', 'audit'] as const)
    it(`platform ${section} requires platform identity and never grants tenant membership`, async () => {
      const adapter = createSyntheticAdapter(0);
      await expect(
        adapter.platformRecords(section, signal()),
      ).rejects.toMatchObject({ code: 'noAccess' });
      await adapter.openReview('admin');
      expect(await adapter.platformRecords(section, signal())).toHaveLength(1);
      await expect(adapter.report(scope, signal())).rejects.toMatchObject({
        code: 'noAccess',
      });
      await expect(adapter.payments(scope, signal())).rejects.toMatchObject({
        code: 'noAccess',
      });
    });
  it('rechecks access after pending reads and denies after logout', async () => {
    const adapter = createSyntheticAdapter(25);
    await adapter.openReview('owner');
    const pending = adapter.payments(scope, signal());
    const check = expect(pending).rejects.toMatchObject({ code: 'noAccess' });
    await adapter.signOut();
    await check;
  });
  it('aborts a pending financial read', async () => {
    const adapter = createSyntheticAdapter(25);
    await adapter.openReview('owner');
    const controller = new AbortController();
    const pending = adapter.payments(scope, controller.signal);
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' });
  });
  it('normal build adapter stays disconnected for all new read projections', async () => {
    await expect(
      disconnectedAdapter.report(scope, signal()),
    ).rejects.toMatchObject({ code: 'notConnected' });
    await expect(
      disconnectedAdapter.payments(scope, signal()),
    ).rejects.toMatchObject({ code: 'notConnected' });
    await expect(
      disconnectedAdapter.platformRecords('audit', signal()),
    ).rejects.toMatchObject({ code: 'notConnected' });
  });
  for (const fields of [
    { reference: 'x' },
    { reference: 'x'.repeat(121) },
    { file: { name: 'a.pdf', type: 'application/pdf', size: 0 } },
    { file: { name: 'a.pdf', type: 'application/pdf', size: 2097153 } },
    { file: { name: 'a.svg', type: 'image/svg+xml', size: 12 } },
  ])
    it(`rejects invalid receipt metadata ${JSON.stringify(fields)}`, () => {
      expect(
        receiptDraftSchema.safeParse({
          reference: 'REVIEW-ONLY',
          file: { name: 'a.pdf', type: 'application/pdf', size: 1 },
          ...fields,
        }).success,
      ).toBe(false);
    });
  it('accepts bounded metadata without loading file content', () => {
    const result = receiptDraftSchema.parse({
      reference: '  REVIEW-ONLY ',
      file: { name: 'review.pdf', type: 'application/pdf', size: 2097152 },
    });
    expect(result.reference).toBe('REVIEW-ONLY');
  });
  it('provides complete nonempty FR/EN/AR catalogs', () => {
    for (const translated of [officeEn, officeAr]) {
      expect(Object.keys(translated).sort()).toEqual(
        Object.keys(officeFr).sort(),
      );
      expect(
        Object.values(translated).every((text) => text.trim().length > 0),
      ).toBe(true);
    }
  });
});
