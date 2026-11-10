// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { PublicMenu } from './local/publicClient';

/** Exact indicative subtotal only; the server still quotes, validates and invoices. */
export function cartSubtotal(
  menu: PublicMenu,
  cart: Readonly<Record<number, string>>,
): string | null {
  const selected = menu.products.filter(
    (product) => Number(cart[product.product_id] ?? '0') !== 0,
  );
  if (!menu.currency || !selected.length) return null;
  let scale = 0;
  for (const product of selected) {
    if (
      !product.orderable ||
      product.unit_price === null ||
      !/^\d+$/.test(cart[product.product_id] ?? '') ||
      Number(cart[product.product_id]) > 100
    )
      return null;
    scale = Math.max(scale, product.unit_price.split('.')[1]?.length ?? 0);
  }
  const total = selected
    .reduce((sum, product) => {
      const [whole, fraction = ''] = product.unit_price!.split('.');
      return (
        sum +
        BigInt(whole! + fraction.padEnd(scale, '0')) *
          BigInt(cart[product.product_id]!)
      );
    }, 0n)
    .toString()
    .padStart(scale + 1, '0');
  return scale ? total.slice(0, -scale) + '.' + total.slice(-scale) : total;
}
