// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { z } from 'zod';
import { LocalDiningClient } from './client';

const id = z.number().int().positive();
const exact = z.string().regex(/^\d+(?:\.\d+)?$/);
const labels = z.object({ fr: z.string(), en: z.string(), ar: z.string() });
export const publicMenu = z.object({
  reference: z.string(),
  restaurant: z.string(),
  branch: z.string(),
  currency: z.string().nullable(),
  precision: z.number().int().nullable(),
  currencies: z.array(z.string()),
  menu_digest: z.string().regex(/^[a-f0-9]{64}$/),
  scan_confirms_presence: z.literal(false),
  availability_certified: z.literal(false),
  table: z.object({
    code: z.string(),
    floor: z.string().nullable(),
    room: z.string().nullable(),
    zone: labels,
    location: labels,
    physical_state: z.string().nullable(),
  }),
  products: z.array(
    z.object({
      product_id: id,
      name: z.string(),
      unit_price: exact.nullable(),
      tariff_id: id.nullable(),
      orderable: z.boolean(),
    }),
  ),
});
export const ownVisit = z.object({
  status: z.enum(['not_signalled', 'pending', 'expired', 'active', 'ended']),
  orders: z.array(
    z.object({
      order_id: id,
      currency: z.string(),
      total: exact,
      status: z.string(),
      lines: z.array(
        z.object({
          product_id: id,
          description: z.string(),
          quantity: z.string(),
          unit_price: exact,
          amount: exact,
          tariff_id: id,
          order_item_id: id,
        }),
      ),
    }),
  ),
});
export const verification = z.object({
  status: z.enum([
    'valid',
    'invalid',
    'invalidated',
    'replaced',
    'cancelled',
    'table_menu',
  ]),
  reference: z.string().optional(),
  kind: z.string().optional(),
  version: z.number().int().optional(),
  digest: z.string().optional(),
});
export type PublicMenu = z.infer<typeof publicMenu>;
export type OwnVisit = z.infer<typeof ownVisit>;
export type Verification = z.infer<typeof verification>;
export const publicId = (value: string) =>
  z
    .string()
    .regex(/^[A-Za-z0-9_-]{43}$/)
    .parse(value);
export function freshVisitSecret(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}
/** Per-tab visitor proof, never a staff identity, QR payload or query parameter. */
export function visitSecret(publicReference: string): string {
  const key = 'moulai-visit:' + publicId(publicReference);
  const current = sessionStorage.getItem(key);
  if (current && /^[A-Za-z0-9_-]{43}$/.test(current)) return current;
  const secret = freshVisitSecret();
  sessionStorage.setItem(key, secret);
  return secret;
}
export class PublicDiningClient {
  constructor(private readonly api = new LocalDiningClient()) {}
  async invoice(reference: string, secret: string): Promise<unknown> {
    return this.api.request(
      '/local-d1/dining/public/invoice',
      'POST',
      { public_id: publicId(reference) },
      { 'X-Visit-Token': secret },
    );
  }
  async menu(reference: string, currency?: string): Promise<PublicMenu> {
    return publicMenu.parse(
      await this.api.request('/local-d1/dining/public/menu', 'POST', {
        public_id: publicId(reference),
        ...(currency ? { currency } : {}),
      }),
    );
  }
  async visit(reference: string, secret: string): Promise<OwnVisit> {
    return ownVisit.parse(
      await this.api.request(
        '/local-d1/dining/public/visit',
        'POST',
        { public_id: publicId(reference) },
        { 'X-Visit-Token': secret },
      ),
    );
  }
  async signal(
    reference: string,
    secret: string,
    party_size: number,
  ): Promise<void> {
    z.object({
      identifier: id,
      status: z.string(),
      expires_at: z.string(),
    }).parse(
      await this.api.request(
        '/local-d1/dining/public/presence',
        'POST',
        { public_id: publicId(reference), party_size },
        { 'X-Visit-Token': secret },
      ),
    );
  }
  async order(
    reference: string,
    secret: string,
    menu: PublicMenu,
    key: string,
    lines: readonly { product_id: number; quantity: number }[],
  ): Promise<void> {
    if (menu.currency === null)
      throw new Error('dining_menu_currency_selection_required');
    z.object({
      identifier: id,
      currency: z.string(),
      total: exact,
      status: z.string(),
    }).parse(
      await this.api.request(
        '/local-d1/dining/public/orders',
        'POST',
        {
          public_id: publicId(reference),
          currency: menu.currency,
          menu_digest: menu.menu_digest,
          idempotency_key: key,
          lines,
        },
        { 'X-Visit-Token': secret },
      ),
    );
  }
  async verify(reference: string): Promise<Verification> {
    return verification.parse(
      await this.api.request('/local-d1/dining/public/verify', 'POST', {
        public_id: publicId(reference),
      }),
    );
  }
}
