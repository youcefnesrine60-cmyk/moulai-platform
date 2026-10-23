// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { z } from 'zod';

export const nameSchema = z.string().trim().min(1).max(255);
export const sortSchema = z.number().int().min(-2147483648).max(2147483647);
export const profileSchema = z
  .object({
    name: nameSchema.min(2),
    type: z.enum([
      'restaurant',
      'cafe',
      'fast_food',
      'bakery',
      'pizza',
      'other',
    ]),
    phone: z
      .string()
      .trim()
      .regex(/^\+?[0-9 -]+$/)
      .transform((value) => value.replace(/[ -]/g, ''))
      .refine((value) => /^\+?\d{9,15}$/.test(value)),
    wilaya: z.string().trim().max(100),
  })
  .strict();
export const categorySchema = z
  .object({ name: nameSchema, sortOrder: sortSchema })
  .strict();
const centimes = z.number().int().nonnegative().max(99999999999);
export const productSchema = z
  .object({
    categoryId: z.number().int().positive(),
    name: nameSchema,
    description: z.string().trim().max(5000),
    price: centimes.positive().max(1000000000),
    available: z.boolean(),
    sortOrder: sortSchema,
  })
  .strict();
export const groupSchema = z
  .object({
    productId: z.number().int().positive(),
    name: nameSchema,
    required: z.boolean(),
    multipleChoice: z.boolean(),
    sortOrder: sortSchema,
  })
  .strict();
export const optionSchema = z
  .object({
    groupId: z.number().int().positive(),
    name: nameSchema,
    extraPrice: centimes.max(100000000),
    available: z.boolean(),
    sortOrder: sortSchema,
  })
  .strict();
export const noteSchema = z.string().trim().max(2000);

/** Parse a decimal DZD input once; reject exponent notation, NaN and precision loss. */
export function parsePrice(value: string, allowZero = false): number | null {
  const normalized = value.trim().replace(',', '.');
  if (!/^\d{1,9}(?:\.\d{1,2})?$/.test(normalized)) return null;
  const [whole = '', fraction = ''] = normalized.split('.');
  const amount = Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
  return Number.isSafeInteger(amount) && (allowZero ? amount >= 0 : amount > 0)
    ? amount
    : null;
}

/** Input formatting stays locale independent; display uses Intl separately. */
export function priceInput(amount: number): string {
  return (amount / 100).toFixed(2);
}
