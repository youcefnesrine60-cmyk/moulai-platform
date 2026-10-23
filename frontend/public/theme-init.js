// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// @ts-check
/** One store initializes before paint and serves React without remounting forms. */
(() => {
  /** @typedef {'light' | 'dark'} Theme */
  /** @typedef {Theme | 'system'} Preference */
  /** @typedef {Readonly<{theme: Theme, preference: Preference}>} Snapshot */
  const key = 'moulai.theme';
  const media =
    typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-color-scheme: dark)')
      : null;
  /** @type {Set<() => void>} */
  const subscribers = new Set();

  /** Read only the appearance key; unavailable storage keeps system behavior. @returns {Preference} */
  function readPreference() {
    try {
      const value = window.localStorage.getItem(key);
      return value === 'light' || value === 'dark' ? value : 'system';
    } catch {
      return 'system';
    }
  }
  /** @param {Preference} preference @returns {Snapshot} */
  function resolve(preference) {
    return Object.freeze({
      preference,
      theme:
        preference === 'system'
          ? media?.matches
            ? 'dark'
            : 'light'
          : preference,
    });
  }
  /** @type {Snapshot} */
  let snapshot = resolve(readPreference());

  /** @param {Preference} preference @returns {void} */
  function apply(preference) {
    const next = resolve(preference);
    const changed =
      next.theme !== snapshot.theme || next.preference !== snapshot.preference;
    snapshot = changed ? next : snapshot;
    document.documentElement.dataset.theme = snapshot.theme;
    document.documentElement.style.colorScheme = snapshot.theme;
    const meta = document.querySelector('meta[name="theme-color"]');
    const background = window
      .getComputedStyle(document.documentElement)
      .getPropertyValue('--surface-page')
      .trim();
    if (meta && background) meta.setAttribute('content', background);
    if (changed) subscribers.forEach((listener) => listener());
  }
  /** @param {Preference} preference @returns {void} */
  function choose(preference) {
    if (!['light', 'dark', 'system'].includes(preference))
      throw new TypeError('Invalid theme preference');
    try {
      if (preference === 'system') window.localStorage.removeItem(key);
      else window.localStorage.setItem(key, preference);
    } catch {
      /* The in-memory preference still works when storage is denied. */
    }
    apply(preference);
  }
  /** @returns {void} */
  function systemChanged() {
    if (snapshot.preference === 'system') apply('system');
  }
  if (media?.addEventListener) media.addEventListener('change', systemChanged);
  window.addEventListener('storage', (event) => {
    if (event.key !== key && event.key !== null) return;
    try {
      if (event.storageArea !== window.localStorage) return;
    } catch {
      return;
    }
    apply(readPreference());
  });
  Object.defineProperty(window, 'moulaiTheme', {
    value: Object.freeze({
      /** @returns {Snapshot} */
      getSnapshot: () => snapshot,
      /** @param {() => void} listener @returns {() => void} */
      subscribe: (listener) => {
        subscribers.add(listener);
        return () => {
          subscribers.delete(listener);
        };
      },
      choose,
    }),
  });
  apply(snapshot.preference);
  document.addEventListener(
    'DOMContentLoaded',
    () => apply(snapshot.preference),
    { once: true },
  );
})();
