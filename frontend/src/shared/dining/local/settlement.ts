// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Exact persisted invoice facts; never calculate financial balances in JavaScript.
import { z } from 'zod';
export const invoiceBalance = z.object({
  status: z.string(),
  invoice_id: z.number().int().positive(),
  currency: z.string(),
  total: z.string(),
  advance: z.string(),
  paid: z.string(),
  balance: z.string(),
  settlement_id: z.number().int().positive().nullable(),
});
export const ownInvoice = z.union([
  invoiceBalance.extend({
    settlement_as_of: z.string().datetime({ offset: true }).optional(),
    document: z
      .discriminatedUnion('status', [
        z.object({ status: z.literal('unissued') }),
        z.object({
          status: z.literal('invalidated'),
          reference: z.string(),
          version: z.number().int().positive(),
        }),
        z.object({
          status: z.literal('origin_unavailable'),
          reference: z.string(),
          version: z.number().int().positive(),
        }),
        z.object({
          status: z.literal('issued'),
          reference: z.string(),
          version: z.number().int().positive(),
          url: z.string().url(),
          qr_svg: z.string(),
          local_only: z.boolean(),
        }),
      ])
      .optional(),
    revision: z.number().int().positive().optional(),
    finalized_at: z.string().datetime({ offset: true }).nullable().optional(),
    lines: z
      .array(
        z.object({
          description: z.string(),
          quantity: z.string().regex(/^\d+(?:\.\d+)?$/),
          unit_price: z.string().regex(/^\d+(?:\.\d+)?$/),
          amount: z.string().regex(/^\d+(?:\.\d+)?$/),
        }),
      )
      .optional(),
  }),
  z.object({ status: z.literal('not_issued') }),
]);
