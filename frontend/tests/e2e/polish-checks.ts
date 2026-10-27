// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { expect, type Page, type TestInfo } from '@playwright/test';

/** Route new captures to the current delivery without overwriting earlier evidence. */
export function evidenceDirectory(info: TestInfo): string {
  const directory = info.config.metadata['evidenceDirectory'];
  return typeof directory === 'string'
    ? directory
    : '../artifacts/frontend-platform-brand-validation';
}

/** Verify compact opaque controls in physical left-to-right order, including Arabic. */
export async function checkHeader(page: Page, info: TestInfo): Promise<void> {
  const header = page.locator('header');
  const measured = await header.evaluate((element) => {
    const frame = element.getBoundingClientRect();
    const logo = element.querySelector('img')!.getBoundingClientRect();
    const controls = [
      ...element.querySelectorAll<HTMLElement>(
        '[role="combobox"], [role="img"]',
      ),
    ];
    return {
      height: frame.height,
      opacity: getComputedStyle(element).opacity,
      background: getComputedStyle(element).backgroundColor,
      center: logo.x + logo.width / 2,
      expectedCenter: frame.x + frame.width / 2,
      logoWidth: logo.width,
      right: frame.right,
      controls: controls.map((control) => {
        const box = control.getBoundingClientRect();
        return {
          x: box.x,
          y: box.y,
          width: box.width,
          height: box.height,
          right: box.right,
          bottom: box.bottom,
          opacity: getComputedStyle(control).opacity,
        };
      }),
      logoBounds: {
        left: logo.left,
        right: logo.right,
        top: logo.top,
        bottom: logo.bottom,
      },
      width: innerWidth,
      overflow: document.documentElement.scrollWidth > innerWidth,
    };
  });
  expect(measured.opacity).toBe('1');
  expect(measured.overflow).toBe(false);
  expect(measured.background).toMatch(/(?:0\.6\)|\/ 0\.6\))/);
  expect(measured.center).toBeCloseTo(measured.expectedCenter, 0);
  // The approved visible signature adds one readable line below the smaller PNG.
  expect(measured.height).toBeLessThan(measured.width <= 1100 ? 300 : 245);
  expect(measured.controls.length).toBeGreaterThanOrEqual(2);
  for (const [index, control] of measured.controls.entries()) {
    expect(control.height).toBe(44);
    expect(control.width).toBeGreaterThanOrEqual(44);
    expect(control.opacity).toBe('1');
    expect(control.y).toBeCloseTo(measured.controls[0]!.y, 0);
    if (index > 0)
      expect(control.x).toBeGreaterThanOrEqual(
        measured.controls[index - 1]!.right,
      );
    const overlapsLogo =
      control.x < measured.logoBounds.right &&
      control.right > measured.logoBounds.left &&
      control.y < measured.logoBounds.bottom &&
      control.bottom > measured.logoBounds.top;
    expect(overlapsLogo).toBe(false);
  }
  expect(measured.right - measured.controls.at(-1)!.right).toBeLessThanOrEqual(
    24,
  );
  await info.attach('header-polish', {
    body: JSON.stringify(measured),
    contentType: 'application/json',
  });
}
