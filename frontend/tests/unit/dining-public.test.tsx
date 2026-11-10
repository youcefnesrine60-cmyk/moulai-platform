// MoulAI™ — local public read/visit contracts never create staff authority.
import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  PublicDiningClient,
  visitSecret,
  freshVisitSecret,
  publicId,
} from '../../src/shared/dining/local/publicClient';
import {
  serviceFr,
  serviceEn,
  serviceAr,
} from '../../src/shared/i18n/diningService';
import { localSections } from '../../src/features/dining/local/navigation';
import type { LocalDiningClient } from '../../src/shared/dining/local/client';
import { cartSubtotal } from '../../src/shared/dining/cartPresentation';
import { publicMenu } from '../../src/shared/dining/local/publicClient';
import { ownInvoice } from '../../src/shared/dining/local/settlement';

afterEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
});
describe('opaque public reads and independently controlled visits', () => {
  it('reads frozen invoice strings and excludes administrative metadata from the UI contract', () => {
    const result = ownInvoice.parse({
      status: 'finalized',
      invoice_id: 1,
      currency: 'DZD',
      total: '1200.00000000',
      advance: '0.00000000',
      paid: '1200.00000000',
      balance: '0.00000000',
      settlement_id: 1,
      finalized_at: '2026-11-10T12:00:00Z',
      revision: 2,
      provenance: { secret: 'synthetic private diagnostic' },
      lines: [
        {
          description: 'Snapshot name',
          quantity: '2',
          unit_price: '600',
          amount: '1200',
          source_reference: 'PRIVATE',
        },
      ],
    });
    expect('lines' in result && result.lines?.[0]).toEqual({
      description: 'Snapshot name',
      quantity: '2',
      unit_price: '600',
      amount: '1200',
    });
    expect(result).not.toHaveProperty('provenance');
  });
  it('shows an exact indicative basket without inventing a payable amount or currency', () => {
    const names = { fr: 'Test', en: 'Test', ar: 'اختبار' };
    const menu = publicMenu.parse({
      reference: 'a'.repeat(43),
      restaurant: 'Test',
      branch: 'Test',
      currency: 'DZD',
      precision: 2,
      currencies: ['DZD'],
      menu_digest: 'a'.repeat(64),
      scan_confirms_presence: false,
      availability_certified: false,
      table: {
        code: '1',
        floor: null,
        room: null,
        physical_state: null,
        zone: names,
        location: names,
      },
      products: [
        {
          product_id: 1,
          name: 'A',
          unit_price: '0.10',
          tariff_id: 1,
          orderable: true,
        },
        {
          product_id: 2,
          name: 'B',
          unit_price: '0.20',
          tariff_id: 2,
          orderable: true,
        },
      ],
    });
    expect(cartSubtotal(menu, { 1: '2', 2: '1' })).toBe('0.40');
    expect(cartSubtotal(menu, { 1: '1.5' })).toBeNull();
    expect(cartSubtotal(menu, { 1: '101' })).toBeNull();
    expect(cartSubtotal({ ...menu, currency: null }, { 1: '1' })).toBeNull();
    expect(
      cartSubtotal(
        { ...menu, products: [{ ...menu.products[0]!, unit_price: null }] },
        { 1: '1' },
      ),
    ).toBeNull();
  });
  it('uses a unique per-tab secret that never equals the public QR or enters the URL', async () => {
    const reference = 'a'.repeat(43),
      secret = visitSecret(reference);
    expect(secret).toMatch(/^[A-Za-z0-9_-]{43}$/);
    expect(secret).not.toBe(reference);
    expect(visitSecret(reference)).toBe(secret);
    expect(visitSecret('b'.repeat(43))).not.toBe(secret);
    const request = vi.fn().mockResolvedValue({
      identifier: 1,
      status: 'pending',
      expires_at: '2026-11-05T20:00:00Z',
    });
    const api = new PublicDiningClient({
      request,
    } as unknown as LocalDiningClient);
    await api.signal(reference, secret, 4);
    expect(request).toHaveBeenCalledWith(
      '/api/web/dining/public/presence',
      'POST',
      { public_id: reference, party_size: 4 },
      { 'X-Visit-Token': secret },
    );
    expect(JSON.stringify(request.mock.calls[0]![2])).not.toContain(secret);
  });
  it('rejects a nonopaque reference before any HTTP request', async () => {
    const request = vi.fn(),
      api = new PublicDiningClient({ request } as unknown as LocalDiningClient);
    await expect(api.menu('restaurant-123')).rejects.toThrow();
    expect(request).not.toHaveBeenCalled();
    expect(() => publicId('x'.repeat(44))).toThrow();
  });
  it('does not turn an arbitrary reply into a verified payment/document', async () => {
    const request = vi.fn().mockResolvedValue({ status: 'paid', total: '100' }),
      api = new PublicDiningClient({ request } as unknown as LocalDiningClient);
    await expect(api.verify('a'.repeat(43))).rejects.toThrow();
  });
  it('retains only safe documented validity data', async () => {
    const request = vi.fn().mockResolvedValue({
        status: 'cancelled',
        reference: 'DOC-LOCAL',
        version: 1,
        customer: 'PRIVATE',
        token: 'SECRET',
        total: '99',
      }),
      api = new PublicDiningClient({ request } as unknown as LocalDiningClient);
    expect(await api.verify('a'.repeat(43))).toEqual({
      status: 'cancelled',
      reference: 'DOC-LOCAL',
      version: 1,
    });
  });
  it('keeps permissions independent from functions and provides kitchen consultation only through explicit powers', () => {
    expect(localSections(['read'])).not.toContain('staff');
    expect(localSections(['orders.prepare'])).toContain('visits');
    expect(localSections(['orders.prepare'])).not.toContain('finance');
    expect(localSections(['clean'])).not.toContain('staff');
  });
  it('covers all new language keys including Arabic without borrowing another language', () => {
    expect(Object.keys(serviceEn).sort()).toEqual(
      Object.keys(serviceFr).sort(),
    );
    expect(Object.keys(serviceAr).sort()).toEqual(
      Object.keys(serviceFr).sort(),
    );
    for (const value of Object.values(serviceAr))
      expect(value.trim()).not.toBe('');
    expect(serviceAr['d1.signalPresence']).toMatch(/[\u0600-\u06ff]/);
  });
  it('generates a fresh retry identifier independently of real dates or a customer identity', () => {
    expect(freshVisitSecret()).toMatch(/^[A-Za-z0-9_-]{43}$/);
    expect(freshVisitSecret()).not.toBe(freshVisitSecret());
  });
});
