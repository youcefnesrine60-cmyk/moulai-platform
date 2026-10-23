// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { describe, expect, it } from 'vitest';
import type { ThemeStore } from '../../src/shared/theme';
import { fr } from '../../src/shared/i18n/fr';
import { en } from '../../src/shared/i18n/en';
import { ar } from '../../src/shared/i18n/ar';
import { businessFr } from '../../src/shared/i18n/business.fr';
import { businessEn } from '../../src/shared/i18n/business.en';
import { businessAr } from '../../src/shared/i18n/business.ar';

const source = readFileSync('public/theme-init.js', 'utf8');
interface StorageObservation {
  key: string | null;
  storageArea: object;
}

/** Execute the production bootstrap with isolated browser capabilities, not a substitute store. */
function boot(stored: string | null = null, dark = false, denied = false) {
  const values = new Map<string, string>();
  if (stored !== null) values.set('moulai.theme', stored);
  const media = {
    matches: dark,
    addEventListener: (_name: string, listener: () => void): void => {
      changed = listener;
    },
  };
  let changed = (): void => {};
  let storageChanged = (_event: StorageObservation): void => {};
  const storage = {
    getItem(key: string): string | null {
      if (denied) throw new Error('Storage denied');
      return values.get(key) ?? null;
    },
    setItem(key: string, value: string): void {
      if (denied) throw new Error('Storage denied');
      values.set(key, value);
    },
    removeItem(key: string): void {
      if (denied) throw new Error('Storage denied');
      values.delete(key);
    },
  };
  const documentElement = {
    dataset: {} as Record<string, string>,
    style: {} as Record<string, string>,
  };
  const fakeDocument = {
    documentElement,
    querySelector: () => null,
    addEventListener: () => {},
  };
  const fakeWindow: {
    localStorage: typeof storage;
    matchMedia: () => typeof media;
    getComputedStyle: () => { getPropertyValue: () => string };
    addEventListener: (
      _name: string,
      listener: (event: StorageObservation) => void,
    ) => void;
    moulaiTheme?: ThemeStore;
  } = {
    localStorage: storage,
    matchMedia: () => media,
    getComputedStyle: () => ({ getPropertyValue: () => '' }),
    addEventListener: (_name, listener) => {
      storageChanged = listener;
    },
  };
  runInNewContext(source, { window: fakeWindow, document: fakeDocument });
  const store = fakeWindow.moulaiTheme;
  if (!store) throw new Error('Theme bootstrap missing');
  return {
    store,
    values,
    documentElement,
    changeSystem: (next: boolean): void => {
      media.matches = next;
      changed();
    },
    changeStorage: (key: string | null, value: string | null): void => {
      if (value === null) values.delete('moulai.theme');
      else values.set('moulai.theme', value);
      storageChanged({ key, storageArea: storage });
    },
  };
}

describe('complete internationalization', () => {
  it('provides every base and business key in English and Arabic', () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(fr).sort());
    expect(Object.keys(fr).every((key) => key in ar)).toBe(true);
    expect(Object.keys(businessEn).sort()).toEqual(
      Object.keys(businessFr).sort(),
    );
    expect(Object.keys(businessAr).sort()).toEqual(
      Object.keys(businessFr).sort(),
    );
    expect(
      [...Object.values(en), ...Object.values(businessEn)].every(
        (value) => value.trim().length > 0,
      ),
    ).toBe(true);
  });
  it('preserves dynamic placeholders in every English translation', () => {
    const reference = { ...fr, ...businessFr };
    const translated = { ...en, ...businessEn };
    for (const key of Object.keys(reference) as (keyof typeof reference)[]) {
      expect(translated[key].match(/\{\{\w+\}\}/g) ?? [], key).toEqual(
        reference[key].match(/\{\{\w+\}\}/g) ?? [],
      );
    }
  });
});

describe('single pre-paint theme store', () => {
  it.each([true, false])(
    'uses system preference when no explicit choice exists (dark=%s)',
    (dark) => {
      const { store, documentElement } = boot(null, dark);
      expect(store.getSnapshot()).toEqual({
        preference: 'system',
        theme: dark ? 'dark' : 'light',
      });
      expect(documentElement.dataset.theme).toBe(dark ? 'dark' : 'light');
      expect(documentElement.style.colorScheme).toBe(dark ? 'dark' : 'light');
    },
  );
  it.each(['light', 'dark'] as const)(
    'honors explicit %s even when the OS disagrees',
    (theme) => {
      const { store, changeSystem } = boot(theme, theme === 'light');
      changeSystem(theme === 'dark');
      expect(store.getSnapshot()).toEqual({ preference: theme, theme });
    },
  );
  it('tracks system changes only while following the system and supports resetting the choice', () => {
    const { store, values, changeSystem } = boot();
    changeSystem(true);
    expect(store.getSnapshot().theme).toBe('dark');
    store.choose('light');
    expect(values.get('moulai.theme')).toBe('light');
    changeSystem(false);
    changeSystem(true);
    expect(store.getSnapshot().theme).toBe('light');
    store.choose('system');
    expect(values.has('moulai.theme')).toBe(false);
    expect(store.getSnapshot().theme).toBe('dark');
  });
  it('rejects unknown values and recovers from stale stored preferences', () => {
    const { store } = boot('sepia', true);
    expect(store.getSnapshot().theme).toBe('dark');
    expect(() => Reflect.apply(store.choose, undefined, ['sepia'])).toThrow(
      'Invalid theme preference',
    );
  });
  it('continues to work without storage access', () => {
    const { store } = boot(null, true, true);
    expect(store.getSnapshot().theme).toBe('dark');
    store.choose('light');
    expect(store.getSnapshot().theme).toBe('light');
  });
  it('keeps snapshots referentially stable and unsubscribes cleanly', () => {
    const { store } = boot('light');
    const first = store.getSnapshot();
    let calls = 0;
    const stop = store.subscribe(() => {
      calls += 1;
    });
    store.choose('light');
    expect(store.getSnapshot()).toBe(first);
    store.choose('dark');
    expect(calls).toBe(1);
    stop();
    store.choose('light');
    expect(calls).toBe(1);
  });
  it('synchronizes appearance across tabs without treating unrelated storage as a theme change', () => {
    const { store, changeStorage } = boot('light');
    changeStorage('moulai.locale', 'dark');
    expect(store.getSnapshot().theme).toBe('light');
    changeStorage('moulai.theme', 'dark');
    expect(store.getSnapshot().theme).toBe('dark');
    changeStorage(null, null);
    expect(store.getSnapshot().preference).toBe('system');
  });
});

/** Relative luminance from the WCAG sRGB transfer function; alpha is not used in tested tokens. */
function luminance(hex: string): number {
  const channels = [1, 3, 5].map((offset) => {
    const value = parseInt(hex.slice(offset, offset + 2), 16) / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return channels[0]! * 0.2126 + channels[1]! * 0.7152 + channels[2]! * 0.0722;
}

describe('semantic token contrast', () => {
  const css = readFileSync('src/shared/styles/tokens.css', 'utf8');
  const declarations = (block: string): Record<string, string> =>
    Object.fromEntries(
      [...block.matchAll(/(--[\w-]+):\s*([^;]+);/g)].map((match) => [
        match[1],
        match[2]!.trim(),
      ]),
    );
  const light = declarations(css.match(/:root\s*\{([\s\S]*?)\}/)?.[1] ?? '');
  const dark = {
    ...light,
    ...declarations(
      css.match(/:root\[data-theme='dark'\]\s*\{([\s\S]*?)\}/)?.[1] ?? '',
    ),
  };
  const resolve = (tokens: Record<string, string>, name: string): string => {
    const value = tokens[name];
    if (!value) throw new Error(`Missing token ${name}`);
    const alias = /^var\((--[\w-]+)\)$/.exec(value);
    if (alias?.[1]) return resolve(tokens, alias[1]);
    if (!/^#[a-f0-9]{6}$/i.test(value))
      throw new Error(`Non-opaque color ${name}`);
    return value;
  };
  for (const [theme, tokens] of [
    ['light', light],
    ['dark', dark],
  ] as const) {
    it.each([
      ['--text-primary', '--surface-card', 4.5],
      ['--text-secondary', '--surface-card', 4.5],
      ['--text-muted', '--surface-page', 4.5],
      ['--accent', '--surface-card', 4.5],
      ['--on-action', '--brand-teal', 4.5],
      ['--on-action', '--action-end', 4.5],
      ['--on-action', '--action-hover-start', 4.5],
      ['--on-action', '--action-hover-end', 4.5],
      ['--review-text', '--review-bg', 4.5],
      ['--neutral-text', '--neutral-bg', 4.5],
      ['--positive-text', '--positive-bg', 4.5],
      ['--sidebar-text', '--surface-sidebar', 4.5],
      ['--sidebar-muted', '--surface-sidebar', 4.5],
      ['--disabled-text', '--disabled-bg', 4.5],
      ['--status-progress-text', '--status-progress-bg', 4.5],
      ['--focus', '--surface-page', 3],
      ['--focus', '--surface-card', 3],
      ['--focus-on-dark', '--surface-sidebar', 3],
      ['--border-strong', '--surface-card', 3],
    ] as const)(
      `${theme}: %s / %s meets %s:1`,
      (foreground, background, minimum) => {
        const a = luminance(resolve(tokens, foreground));
        const b = luminance(resolve(tokens, background));
        expect(
          (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05),
        ).toBeGreaterThanOrEqual(minimum);
      },
    );
  }
});
