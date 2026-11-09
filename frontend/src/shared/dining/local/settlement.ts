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
  invoiceBalance,
  z.object({ status: z.literal('not_issued') }),
]);
