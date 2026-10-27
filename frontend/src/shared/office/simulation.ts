import { z } from 'zod';
import { parsePrice } from '../business/validation';
import type { BillingWorkspace, PaymentView } from './contracts';

/** Mirrors bounded form inputs, never a backend authorization or settlement decision. */
export const verificationSchema = z
  .object({
    decision: z.enum(['approve', 'reject']),
    fundsReceived: z.boolean(),
    reference: z.string().trim().max(120),
    amount: z.string().trim(),
    currency: z.enum(['', 'DZD']),
    note: z.string().trim().min(3).max(2000),
  })
  .strict();
export type VerificationDraft = z.infer<typeof verificationSchema>;

function normalizedReference(value: string): string | null {
  if (!/^[A-Za-z0-9 ./_-]{3,120}$/.test(value)) return null;
  const result = value.replace(/[ ./_-]/g, '').toUpperCase();
  return result.length >= 3 ? result : null;
}

/** Pure preview: never mutates a payment, receipt, subscription or audit record. */
export function simulateVerification(
  payment: PaymentView,
  input: unknown,
): 'approve' | 'reject' | null {
  const parsed = verificationSchema.safeParse(input);
  if (
    !parsed.success ||
    payment.status !== 'pending' ||
    payment.receipt?.reviewStatus !== 'pending'
  )
    return null;
  const d = parsed.data;
  if (d.decision === 'reject')
    return !d.fundsReceived && !d.reference && !d.amount && !d.currency
      ? 'reject'
      : null;
  const reference = normalizedReference(d.reference);
  return d.fundsReceived &&
    d.currency === payment.currency &&
    parsePrice(d.amount) === payment.amount &&
    reference !== null &&
    reference === normalizedReference(payment.receipt.reference)
    ? 'approve'
    : null;
}

export const checkoutDraftSchema = z
  .object({
    planId: z.number().int().positive(),
    cycle: z.enum(['monthly', 'yearly']),
    method: z.enum(['ccp', 'baridimob']),
  })
  .strict();

/** A UI preview of a selected synthetic quote, not an invoice or a server-calculated price. */
export function checkoutPreview(
  workspace: BillingWorkspace,
  input: unknown,
): number | null {
  const parsed = checkoutDraftSchema.safeParse(input);
  if (!parsed.success) return null;
  const { planId, cycle, method } = parsed.data;
  if (!workspace.instructions.some((i) => i.method === method && i.enabled))
    return null;
  const offer = workspace.offers.find((o) => o.id === planId);
  const amount = offer?.[cycle];
  return amount !== undefined && Number.isSafeInteger(amount) && amount > 0
    ? amount
    : null;
}
