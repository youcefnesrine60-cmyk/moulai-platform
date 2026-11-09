// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { z } from 'zod';
import type { DiningOperation, JsonValue } from './operations';

const id = z.number().int().positive();
// PostgreSQL Numeric and immutable quote JSON can use exact exponent notation.
// Expand text without converting a monetary value through binary floating point.
const decimal = z
  .string()
  .regex(/^\d+(?:\.\d+)?(?:[eE][+-]?\d{1,2})?$/)
  .transform((value) => {
    const [mantissa, exponent] = value.toLowerCase().split('e');
    if (exponent === undefined) return value;
    const [whole, fraction = ''] = mantissa!.split('.');
    const digits = whole! + fraction;
    const point = whole!.length + Number(exponent);
    if (point <= 0) return '0.' + '0'.repeat(-point) + digits;
    if (point >= digits.length)
      return digits + '0'.repeat(point - digits.length);
    return digits.slice(0, point) + '.' + digits.slice(point);
  });
const record = z.object({ id });
export const reference = record.extend({
  kind: z.string(),
  code: z.string(),
  labels: z.object({ fr: z.string(), en: z.string(), ar: z.string() }),
  active: z.boolean(),
  pricing_ref: z.string().nullable(),
});
export const table = record.extend({
  code: z.string(),
  name: z.string().nullable(),
  min_capacity: z.number(),
  max_capacity: z.number(),
  shape_id: id,
  category_id: id,
  zone_id: id,
  location_id: id,
  description: z.string(),
  floor_label: z.string().nullable().optional(),
  room_label: z.string().nullable().optional(),
  photos: z.array(z.string()),
  pricing_ref: z.string(),
  in_service: z.boolean(),
  physical_state: z.string(),
  revision: z.number(),
});
export const request = record.extend({
  reference: z.string(),
  status: z.string(),
  starts_at: z.string(),
  ends_at: z.string(),
  party_size: z.number(),
  customer_name: z.string().optional(),
  contact: z.string().optional(),
  event_id: id.nullable(),
  preparation: z.boolean(),
  menu: z.array(z.object({ product_id: id, quantity: z.string() })),
});
export const quote = record.extend({
  request_id: id,
  version: z.number(),
  currency: z.string(),
  amount: decimal,
  digest: z.string(),
  expires_at: z.string(),
  terms: z.string(),
  components: z.array(
    z.object({
      kind: z.string(),
      currency_precision: z.number().optional(),
      quantity: z.string(),
      rate: decimal,
      amount: decimal,
      description: z.string().optional(),
    }),
  ),
});
const policy = z.object({
  timezone: z.string(),
  response_seconds: z.number(),
  hold_seconds: z.number(),
  lateness_seconds: z.number(),
  preparation_seconds: z.number(),
  cleaning_seconds: z.number(),
  confirmation_seconds: z.number(),
  confirmation_scope: z.literal('tables'),
  alert_offsets_seconds: z.array(z.number()),
  service_recipients: z.array(id),
  escalation_recipients: z.array(id),
  currencies: z.record(z.number().int()),
  payment_instructions: z.record(z.string()),
  terms: z.string(),
});
const scope = z.object({
  organization_id: id,
  restaurant_id: id,
  branch_id: id,
  role: z.string(),
  restaurant_name: z.string().optional(),
  branch_name: z.string().optional(),
});
const session = z.object({
  actor: z.string(),
  identity_provider: z.enum(['simulated-local-rs256', 'keycloak-local']),
  persistence: z.string().optional(),
  scopes: z.array(scope),
  customer_proofs: z.record(z.string()),
});
const snapshot = z.object({
  source: z.literal('postgres-local'),
  capabilities: z.array(z.string()),
  staff_profiles: z
    .array(
      record.extend({
        membership_id: id,
        employee_code: z.string(),
        display_name: z.string(),
        enrollment_generation: z.number(),
        accepted_at: z.string().nullable(),
      }),
    )
    .optional(),
  staff_functions: z
    .array(
      record.extend({
        code: z.string(),
        labels: z.object({ fr: z.string(), en: z.string(), ar: z.string() }),
        tasks: z.array(z.string()),
        active: z.boolean(),
      }),
    )
    .optional(),
  staff_assignments: z
    .array(
      record.extend({
        membership_id: id,
        function_id: id,
        active: z.boolean(),
        assigned_by: id,
      }),
    )
    .optional(),
  server_time: z.string().optional(),
  policy: policy.nullable().optional(),
  references: z.array(reference).optional(),
  tables: z.array(table).optional(),
  traits: z
    .array(record.extend({ table_id: id, reference_id: id, kind: z.string() }))
    .optional(),
  combinations: z
    .array(
      record.extend({
        code: z.string(),
        min_capacity: z.number(),
        max_capacity: z.number(),
        pricing_ref: z.string(),
        active: z.boolean(),
      }),
    )
    .optional(),
  members: z
    .array(record.extend({ combination_id: id, table_id: id }))
    .optional(),
  calendar: z
    .array(
      record.extend({
        weekday: z.number().nullable(),
        service_date: z.string().nullable(),
        windows: z.array(
          z.object({
            start: z.string(),
            end: z.string(),
            next_day: z.boolean(),
            start_fold: z.number().nullable().optional(),
            end_fold: z.number().nullable().optional(),
          }),
        ),
      }),
    )
    .optional(),
  blackouts: z
    .array(
      record.extend({
        starts_at: z.string(),
        ends_at: z.string(),
        kind: z.string(),
        reason: z.string(),
        active: z.boolean(),
        table_id: id.nullable(),
        zone_id: id.nullable(),
      }),
    )
    .optional(),
  requests: z.array(request).optional(),
  request_tables: z
    .array(record.extend({ request_id: id, table_id: id }))
    .optional(),
  quotes: z.array(quote).optional(),
  acceptances: z
    .array(
      record.extend({ quote_id: id, party: z.string(), digest: z.string() }),
    )
    .optional(),
  receipts: z
    .array(
      record.extend({
        request_id: id,
        quote_id: id.optional(),
        currency: z.string(),
        received_amount: decimal,
        expected_amount: decimal.optional(),
        status: z.string(),
        reference: z.string().optional(),
      }),
    )
    .optional(),
  invoices: z
    .array(
      record.extend({
        request_id: id.nullable(),
        occupation_id: id.nullable().optional(),
        status: z.string(),
        currency: z.string(),
        total: decimal,
        revision: z.number(),
        precision: z.number(),
      }),
    )
    .optional(),
  allocations: z
    .array(
      record.extend({
        request_id: id,
        receipt_id: id,
        invoice_id: id,
        currency: z.string(),
        amount: decimal,
        balance: decimal,
        invoice_total: decimal,
      }),
    )
    .optional(),
  occupations: z
    .array(
      record.extend({
        request_id: id.nullable(),
        status: z.string(),
        party_size: z.number(),
        arrived_at: z.string(),
        expected_end: z.string(),
        cleaning_expected_start: z.string().optional(),
        cleaning_expected_end: z.string(),
        departed_at: z.string().nullable(),
        cleaning_actual_start: z.string().nullable(),
        cleaning_actual_end: z.string().nullable(),
      }),
    )
    .optional(),
  occupation_tables: z
    .array(
      record.extend({ occupation_id: id, table_id: id, active: z.boolean() }),
    )
    .optional(),
  claims: z
    .array(
      record.extend({
        request_id: id.nullable(),
        table_id: id,
        kind: z.string(),
        starts_at: z.string(),
        ends_at: z.string(),
        active: z.boolean(),
        expires_at: z.string().nullable(),
      }),
    )
    .optional(),
  confirmations: z
    .array(
      record.extend({
        request_id: id.nullable(),
        valid_until: z.string(),
        starts_at: z.string(),
        ends_at: z.string(),
        membership_id: id,
      }),
    )
    .optional(),
  tariffs: z
    .array(
      record.extend({
        reference: z.string(),
        component: z.string(),
        currency: z.string(),
        unit: z.string(),
        unit_price: decimal,
        valid_from: z.string(),
        valid_until: z.string().nullable(),
      }),
    )
    .optional(),
  grants: z
    .array(
      record.extend({
        membership_id: id,
        capability: z.string(),
        actor_kind: z.string(),
        active: z.boolean(),
      }),
    )
    .optional(),
  memberships: z
    .array(
      record.extend({
        role: z.string(),
        status: z.string(),
        revision: z.number().optional(),
        enrollment_generation: z.number().optional(),
      }),
    )
    .optional(),
  products: z
    .array(
      record.extend({
        name: z.string(),
        is_available: z.boolean().nullable(),
        legacy_price: z.string(),
      }),
    )
    .optional(),
  food_orders: z
    .array(
      record.extend({
        table_id: id.nullable(),
        status: z.string(),
        legacy_total: z.string(),
        items: z.array(
          record.extend({
            description: z.string(),
            quantity: z.number(),
            legacy_unit_price: z.string(),
          }),
        ),
      }),
    )
    .optional(),
  public_links: z
    .array(
      record.extend({
        public_id: z.string().regex(/^[A-Za-z0-9_-]{43}$/),
        reference: z.string(),
        kind: z.enum(['table', 'reservation', 'food_invoice', 'receipt']),
        version: z.number().int(),
        generation: z.number().int(),
        active: z.boolean(),
        table_id: id.nullable(),
        request_id: id.nullable(),
        invoice_id: id.nullable(),
        receipt_id: id.nullable(),
      }),
    )
    .optional(),
  presence_signals: z
    .array(
      record.extend({
        table_id: id,
        party_size: z.number().int(),
        status: z.string(),
        expires_at: z.string(),
      }),
    )
    .optional(),
  visits: z
    .array(
      record.extend({
        table_id: id,
        occupation_id: id,
        presence_id: id,
        status: z.string(),
        ended_at: z.string().nullable(),
      }),
    )
    .optional(),
  visit_orders: z
    .array(
      record.extend({
        visit_id: id,
        order_id: id,
        currency: z.string(),
        total: decimal,
        exact_lines: z.array(
          z.object({
            product_id: id,
            order_item_id: id,
            description: z.string(),
            quantity: z.string(),
            unit_price: decimal,
            amount: decimal,
            tariff_id: id,
          }),
        ),
      }),
    )
    .optional(),
  service_events: z
    .array(
      record.extend({
        kind: z.string(),
        occurred_at: z.string(),
        details: z.record(
          z.union([z.string(), z.number(), z.boolean(), z.null()]),
        ),
      }),
    )
    .optional(),
  event_transport: z.literal('local-persisted-no-delivery').optional(),
  events: z
    .array(
      record.extend({
        kind: z.string(),
        occurred_at: z.string(),
        author: z.record(z.unknown()),
        details: z.record(z.unknown()),
      }),
    )
    .optional(),
  outbox: z
    .array(
      record.extend({
        status: z.string(),
        event_key: z.string(),
        attempts: z.number(),
        delivery_reference: z.string().nullable(),
      }),
    )
    .optional(),
});

export type LocalScope = z.infer<typeof scope>;
export type LocalSession = z.infer<typeof session>;
export type Snapshot = z.infer<typeof snapshot>;
export type StoredRequest = z.infer<typeof request>;
export type StoredQuote = z.infer<typeof quote>;
export type StoredTable = z.infer<typeof table>;
export type Policy = z.infer<typeof policy>;
export class LocalDiningError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
  ) {
    super(code);
  }
}
export type OperationResult = Readonly<Record<string, JsonValue>>;

/** Same-origin only. No retries, optimistic financial writes, credential logging or storage. */
export class LocalDiningClient {
  constructor(readonly operational = false) {}
  url(path: string): string {
    return this.operational
      ? path.replace(/^\/local-d1(?=\/|$)/, '/api/web')
      : path;
  }

  private generation = 0;
  private identity: LocalSession | null = null;
  async request(
    path: string,
    method = 'GET',
    body?: unknown,
    headers: Readonly<Record<string, string>> = {},
  ): Promise<unknown> {
    const generation = this.generation;
    const response = await fetch(this.url(path), {
      method,
      credentials: 'same-origin',
      cache: 'no-store',
      headers: {
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...headers,
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    const data: unknown = await response.json();
    if (generation !== this.generation)
      throw new LocalDiningError(409, 'identity_changed');
    if (!response.ok) {
      if (this.operational && response.status === 401)
        window.dispatchEvent(new Event('moulai-session-expired'));
      const error = z.object({ detail: z.unknown() }).safeParse(data);
      const detail = error.success ? error.data.detail : null;
      const code =
        typeof detail === 'object' &&
        detail !== null &&
        'code' in detail &&
        typeof detail.code === 'string'
          ? detail.code
          : 'request_refused';
      throw new LocalDiningError(response.status, code);
    }
    return data;
  }
  async signIn(actor: string): Promise<LocalSession> {
    if (this.operational)
      throw new LocalDiningError(403, 'review_identity_forbidden');
    this.generation++;
    this.identity = null;
    await this.request('/local-d1/session', 'POST', { actor });
    return this.currentSession();
  }
  async currentSession(): Promise<LocalSession> {
    this.identity = session.parse(
      await this.request(
        this.operational ? '/api/web/dining-session' : '/local-d1/session',
      ),
    );
    if (
      this.identity.identity_provider !==
      (this.operational ? 'keycloak-local' : 'simulated-local-rs256')
    )
      throw new LocalDiningError(401, 'identity_provider_mismatch');
    return this.identity;
  }
  async signOut(): Promise<void> {
    this.generation++;
    this.identity = null;
    await this.request(
      this.operational ? '/api/web/auth/logout' : '/local-d1/session',
      this.operational ? 'POST' : 'DELETE',
    );
  }
  root(scope: LocalScope): string {
    return `/local-d1/organizations/${scope.organization_id}/restaurants/${scope.restaurant_id}/branches/${scope.branch_id}/dining`;
  }
  async workspace(scope: LocalScope): Promise<Snapshot> {
    const path =
      this.identity?.actor === 'customer'
        ? `/local-d1/dining/restaurants/${scope.restaurant_id}/branches/${scope.branch_id}/customer-workspace`
        : this.root(scope) + '/workspace';
    return snapshot.parse(await this.request(path));
  }
  async command(
    scope: LocalScope,
    command: DiningOperation,
  ): Promise<OperationResult> {
    const proof = this.identity?.customer_proofs[String(scope.branch_id)];
    return (await this.request(
      this.root(scope) + '/commands',
      'POST',
      command,
      proof ? { 'X-Customer-Proof': proof } : {},
    )) as OperationResult;
  }
  async instant(
    scope: LocalScope,
    value: string,
    fold: string = '',
  ): Promise<string> {
    const [day, wall_time] = value.split('T');
    if (!day || !wall_time) throw new LocalDiningError(422, 'date_required');
    const query = new URLSearchParams({
      day,
      wall_time,
      ...(fold === '' ? {} : { fold }),
    });
    return z
      .object({ instant: z.string() })
      .parse(await this.request(this.root(scope) + `/instant?${query}`))
      .instant;
  }
  async receipt(
    scope: LocalScope,
    data: {
      request_id: number;
      quote_id: number;
      received_amount: string;
      currency: string;
      mode: string;
      reference: string;
      received_at: string;
    },
  ): Promise<OperationResult> {
    return (await this.request(
      this.root(scope) + '/receipts',
      'POST',
      data,
    )) as OperationResult;
  }
  async accept(
    scope: LocalScope,
    quoteId: number,
    digest: string,
  ): Promise<OperationResult> {
    return (await this.request(
      `/local-d1/dining/restaurants/${scope.restaurant_id}/branches/${scope.branch_id}/quotes/${quoteId}/accept`,
      'POST',
      { digest },
    )) as OperationResult;
  }
  async requestCancellation(
    scope: LocalScope,
    requestId: number,
    reason: string,
  ): Promise<OperationResult> {
    return (await this.request(
      `/local-d1/dining/restaurants/${scope.restaurant_id}/branches/${scope.branch_id}/requests/${requestId}/cancellation-request`,
      'POST',
      { reason },
    )) as OperationResult;
  }
  printUrl(scope: LocalScope, requestId: number, locale: string): string {
    return this.url(
      (this.identity?.actor === 'customer'
        ? `/local-d1/dining/restaurants/${scope.restaurant_id}/branches/${scope.branch_id}/requests/${requestId}/confirmation`
        : this.root(scope) + `/requests/${requestId}/confirmation`) +
        `?locale=${encodeURIComponent(locale)}`,
    );
  }
}

const planning = z.array(
  z.object({
    id,
    code: z.string(),
    physical_state: z.string(),
    in_service: z.boolean(),
    capacity_min: z.number(),
    capacity_max: z.number(),
    fully_reserved: z.boolean(),
    closed: z.boolean(),
    occupation: z
      .object({
        id,
        arrived_at: z.string(),
        expected_end: z.string(),
        departed_at: z.string().nullable(),
        cleaning_expected_end: z.string(),
      })
      .nullable(),
    opening: z.array(z.object({ start: z.string(), end: z.string() })),
    claims: z.array(
      z.object({
        kind: z.string(),
        start: z.string(),
        end: z.string(),
        request_id: id.nullable(),
      }),
    ),
  }),
);
export type Planning = z.infer<typeof planning>;
export async function readPlanning(
  api: LocalDiningClient,
  scope: LocalScope,
  day: string,
): Promise<Planning> {
  const next = new Date(Date.parse(day + 'T12:00:00Z') + 86400000)
    .toISOString()
    .slice(0, 10);
  const start = await api.instant(scope, day + 'T00:00:00');
  const end = await api.instant(scope, next + 'T00:00:00');
  return planning.parse(
    await api.request(
      api.root(scope) +
        '/planning?' +
        new URLSearchParams({ starts_at: start, ends_at: end }),
    ),
  );
}
