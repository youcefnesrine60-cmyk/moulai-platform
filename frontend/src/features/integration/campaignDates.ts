// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// MoulAI™ — explicit UTC campaign inputs, with unchanged sub-millisecond instants preserved.
export function campaignDateInput(value: string | null): string {
  return value ? new Date(value).toISOString().slice(0, -1) : '';
}

/** Never infer a device timezone or DST fold for a platform campaign. */
export function campaignDateValue(
  value: string,
  original: string | null,
): string {
  if (original && value === campaignDateInput(original)) return original;
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:[.]\d{1,3})?)?$/.test(value))
    throw new Error('invalid_utc_campaign_input');
  const instant = new Date(value + 'Z').toISOString();
  if (instant.slice(0, 16) !== value.slice(0, 16))
    throw new Error('invalid_utc_campaign_day');
  return instant;
}
