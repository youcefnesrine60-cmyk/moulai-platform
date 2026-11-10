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

afterEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
});
describe('opaque public reads and independently controlled visits', () => {
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
