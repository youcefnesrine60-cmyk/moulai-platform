import { z } from 'zod';

/** Client-side metadata validation is a preview; server byte/signature checks remain mandatory. */
export const receiptDraftSchema = z.object({
  reference: z.string().trim().min(3).max(120),
  file: z.object({
    name: z.string().min(1),
    size: z
      .number()
      .int()
      .positive()
      .max(2 * 1024 * 1024),
    type: z.enum(['image/png', 'image/jpeg', 'application/pdf']),
  }),
});
