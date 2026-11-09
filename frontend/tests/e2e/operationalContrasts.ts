// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { Page } from '@playwright/test';

/** Measure actual computed opaque surfaces, not just the hex constants in a design spec. */
export async function operationalContrasts(page: Page) {
  return page.evaluate(() => {
    function luminance(color: string) {
      const channels = color
        .match(/[\d.]+/g)
        ?.slice(0, 3)
        .map(Number);
      if (!channels || channels.length !== 3)
        throw new Error('Opaque computed RGB required');
      const linear = channels.map((n) => {
        const c = n / 255;
        return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * linear[0]! + 0.7152 * linear[1]! + 0.0722 * linear[2]!;
    }
    function contrast(a: string, b: string) {
      const x = luminance(a),
        y = luminance(b);
      return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
    }
    const metrics: { kind: string; text: number; border: number }[] = [];
    for (const element of document.querySelectorAll(
      '[data-testid="operational-board"] [data-ui-tone], [data-table-card], [data-testid="operational-board"] button',
    )) {
      const style = getComputedStyle(element);
      if (style.backgroundColor === 'rgba(0, 0, 0, 0)') continue;
      metrics.push({
        kind:
          element.getAttribute('data-ui-tone') ??
          element.getAttribute('data-state') ??
          'filter-button',
        text: contrast(style.color, style.backgroundColor),
        border: contrast(style.borderInlineStartColor, style.backgroundColor),
      });
    }
    const focused = document.querySelector(
      '[data-testid="physical-filter-reset"]',
    );
    if (!focused) throw new Error('Focused reset missing');
    const focusedStyle = getComputedStyle(focused);
    const focus = contrast(
      focusedStyle.outlineColor,
      focusedStyle.backgroundColor,
    );
    const disabled = document.querySelector<HTMLButtonElement>(
      'form[data-operation="arrival"] button[type="submit"]',
    );
    if (!disabled) throw new Error('Real disabled action style required');
    disabled.disabled = true;
    const disabledStyle = getComputedStyle(disabled);
    const disabledText = contrast(
      disabledStyle.color,
      disabledStyle.backgroundColor,
    );
    disabled.disabled = false;
    return { metrics, focus, disabledText };
  });
}
