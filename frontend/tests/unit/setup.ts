// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach, vi } from 'vitest';
import '../../src/shared/i18n';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

// Execute the actual parser-blocking bootstrap once in each isolated test window.
runInNewContext(readFileSync('public/theme-init.js', 'utf8'), {
  window,
  document,
});

// Lazy feature imports and dependent scoped reads can exceed the one-second default.
configure({ asyncUtilTimeout: 3000 });

// jsdom has no pointer-capture or layout scrolling; actual behavior is browser-tested.
const capturedPointers = new WeakMap<HTMLElement, Set<number>>();
HTMLElement.prototype.hasPointerCapture = function (
  pointerId: number,
): boolean {
  return capturedPointers.get(this)?.has(pointerId) ?? false;
};
HTMLElement.prototype.setPointerCapture = function (pointerId: number): void {
  const pointers = capturedPointers.get(this) ?? new Set<number>();
  pointers.add(pointerId);
  capturedPointers.set(this, pointers);
};
HTMLElement.prototype.releasePointerCapture = function (
  pointerId: number,
): void {
  capturedPointers.get(this)?.delete(pointerId);
};
HTMLElement.prototype.scrollIntoView = vi.fn();
// Radix observes popup geometry; jsdom cannot supply layout dimensions.
vi.stubGlobal(
  'ResizeObserver',
  class {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  },
);

afterEach(() => {
  cleanup();
  localStorage.clear();
});
