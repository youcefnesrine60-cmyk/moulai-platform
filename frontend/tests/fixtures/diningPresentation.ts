// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type {
  Snapshot,
  Planning,
  LocalSession,
} from '../../src/shared/dining/local/client';

/** Read-only visual responses, never a seed or a source of business writes. */
export function diningPresentationFixture(locale: 'fr' | 'en' | 'ar') {
  const scope = {
    organization_id: 10,
    restaurant_id: 200,
    branch_id: 300,
    role: 'owner',
    restaurant_name: 'Bistro MoulAI — Démonstration',
    branch_name: 'Centre-ville — Démonstration',
  };
  const session: LocalSession = {
    actor: 'owner',
    identity_provider: 'simulated-local-rs256',
    scopes: [scope],
    customer_proofs: {},
  };
  const labels = {
    fr: 'Terrasse panoramique et espace événementiel accessible',
    en: 'Panoramic terrace and accessible private event space',
    ar: 'الشرفة البانورامية ومساحة المناسبات الخاصة المهيأة للضيوف',
  };
  const reason = {
    fr: 'Réparation du piètement et contrôle de stabilité avant remise en service',
    en: 'Base repair and stability inspection required before returning to service',
    ar: 'إصلاح قاعدة الطاولة وفحص ثباتها قبل إعادتها إلى الخدمة',
  };
  const states = [
    'available',
    'occupied',
    'dirty',
    'maintenance',
    'out_of_service',
    'available',
    'out_of_service',
  ];
  const tables = states.map((state, index) => ({
    id: index + 1,
    code: `T${String(index + 1).padStart(2, '0')}`,
    name: null,
    min_capacity: 2,
    max_capacity: 6,
    shape_id: 101,
    category_id: 102,
    zone_id: 103,
    location_id: 104,
    description: '',
    photos: [],
    pricing_ref: 'visual-fixture-not-a-commercial-tariff',
    in_service: state !== 'out_of_service',
    physical_state: state,
    revision: 1,
  }));
  const occupations = [
    {
      id: 21,
      request_id: null,
      status: 'occupied',
      party_size: 4,
      arrived_at: '2026-11-03T16:30:00Z',
      expected_end: '2026-11-03T17:50:00Z',
      cleaning_expected_start: '2026-11-03T17:50:00Z',
      cleaning_expected_end: '2026-11-03T18:05:00Z',
      departed_at: null,
      cleaning_actual_start: null,
      cleaning_actual_end: null,
    },
    {
      id: 22,
      request_id: null,
      status: 'cleaning',
      party_size: 2,
      arrived_at: '2026-11-03T16:00:00Z',
      expected_end: '2026-11-03T17:45:00Z',
      cleaning_expected_start: '2026-11-03T17:45:00Z',
      cleaning_expected_end: '2026-11-03T18:15:00Z',
      departed_at: '2026-11-03T17:50:00Z',
      cleaning_actual_start: '2026-11-03T17:55:00Z',
      cleaning_actual_end: null,
    },
  ];
  const requests = [
    {
      id: 31,
      reference: 'VISUAL-CONFIRMED',
      status: 'confirmed',
      starts_at: '2026-11-03T19:00:00Z',
      ends_at: '2026-11-03T22:00:00Z',
      party_size: 4,
      customer_name: 'Synthetic visual customer',
      contact: 'visual@example.invalid',
      event_id: null,
      preparation: false,
      menu: [],
    },
    {
      id: 32,
      reference: 'VISUAL-HELD',
      status: 'held',
      starts_at: '2026-11-03T18:30:00Z',
      ends_at: '2026-11-03T20:00:00Z',
      party_size: 2,
      event_id: null,
      preparation: false,
      menu: [],
    },
  ];
  const claims = [
    {
      id: 41,
      request_id: 31,
      table_id: 1,
      kind: 'reservation',
      starts_at: '2026-11-03T19:00:00Z',
      ends_at: '2026-11-03T22:00:00Z',
      active: true,
      expires_at: null,
    },
    {
      id: 42,
      request_id: 32,
      table_id: 6,
      kind: 'hold',
      starts_at: '2026-11-03T18:30:00Z',
      ends_at: '2026-11-03T20:00:00Z',
      active: true,
      expires_at: '2026-11-03T18:20:00Z',
    },
  ];
  claims.push({ ...claims[0]!, id: 43, table_id: 2 });
  const workspace: Snapshot = {
    source: 'postgres-local',
    server_time: '2026-11-03T18:00:00Z',
    capabilities: [
      'read',
      'configure',
      'service',
      'clean',
      'collect',
      'finance.read',
      'invoices.create',
      'invoices.finalize',
      'advances.allocate',
    ],
    policy: {
      timezone: 'Africa/Algiers',
      response_seconds: 60,
      hold_seconds: 1200,
      lateness_seconds: 300,
      preparation_seconds: 0,
      cleaning_seconds: 900,
      confirmation_seconds: 7200,
      confirmation_scope: 'tables',
      alert_offsets_seconds: [60],
      service_recipients: [1],
      escalation_recipients: [],
      currencies: { DZD: 2 },
      payment_instructions: { cash: 'VISUAL FIXTURE — NO COLLECTION' },
      terms: 'Synthetic presentation only',
    },
    references: [
      {
        id: 103,
        kind: 'zone',
        code: 'visual-zone',
        labels,
        active: true,
        pricing_ref: null,
      },
      {
        id: 104,
        kind: 'location',
        code: 'visual-floor',
        labels: {
          fr: 'Rez-de-chaussée',
          en: 'Ground floor',
          ar: 'الطابق الأرضي',
        },
        active: true,
        pricing_ref: null,
      },
    ],
    tables,
    occupations,
    occupation_tables: [
      { id: 51, occupation_id: 21, table_id: 2, active: true },
      { id: 52, occupation_id: 22, table_id: 3, active: true },
    ],
    claims,
    requests,
    request_tables: [
      { id: 61, request_id: 31, table_id: 1 },
      { id: 62, request_id: 32, table_id: 6 },
    ],
    quotes: [
      {
        id: 71,
        request_id: 32,
        version: 1,
        currency: 'DZD',
        amount: '1500.00',
        digest: 'a'.repeat(64),
        expires_at: '2026-11-03T19:00:00Z',
        terms: 'Presentation only',
        components: [],
      },
    ],
    receipts: [],
    confirmations: [],
    blackouts: [
      {
        id: 81,
        starts_at: '2026-11-03T17:00:00Z',
        ends_at: '2026-11-03T22:00:00Z',
        kind: 'maintenance',
        reason: reason[locale],
        active: true,
        table_id: 4,
        zone_id: null,
      },
      {
        id: 82,
        starts_at: '2026-11-03T17:00:00Z',
        ends_at: '2026-11-03T23:00:00Z',
        kind: 'closure',
        reason: reason[locale],
        active: true,
        table_id: 7,
        zone_id: null,
      },
    ],
  };
  const planning: Planning = tables.map((table) => ({
    id: table.id,
    code: table.code,
    physical_state: table.physical_state,
    in_service: table.in_service,
    capacity_min: table.min_capacity,
    capacity_max: table.max_capacity,
    fully_reserved: table.id === 1,
    closed: [4, 7].includes(table.id),
    occupation:
      occupations.find(
        (row) => row.id === (table.id === 2 ? 21 : table.id === 3 ? 22 : 0),
      ) ?? null,
    opening:
      table.id === 1
        ? [{ start: '2026-11-03T19:00:00Z', end: '2026-11-03T22:00:00Z' }]
        : [{ start: '2026-11-03T07:00:00Z', end: '2026-11-03T23:00:00Z' }],
    claims: claims
      .filter((row) => row.table_id === table.id)
      .map((row) => ({
        kind: row.kind,
        start: row.starts_at,
        end: row.ends_at,
        request_id: row.request_id,
      })),
  }));
  return { session, workspace, planning };
}
