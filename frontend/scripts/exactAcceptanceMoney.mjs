// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Exact rational comparison for acceptance assertions; never reuse formatted UI floats.
import assert from 'node:assert/strict';
/** Quantize an exact decimal and rational multiplier once, using HALF_UP. */
export function roundedCents(value, multiplier = 1n, divisor = 1n) {
  const m = /^(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(String(value));
  assert(m, 'An exact nonnegative decimal is required');
  const exponent = Number(m[3] ?? 0);
  assert(Number.isSafeInteger(exponent) && Math.abs(exponent) <= 100);
  const scale = (m[2] ?? '').length - exponent;
  let n = BigInt(m[1] + (m[2] ?? '')) * 100n * multiplier;
  let d = divisor;
  if (scale >= 0) d *= 10n ** BigInt(scale);
  else n *= 10n ** BigInt(-scale);
  return (2n * n + d) / (2n * d);
}
