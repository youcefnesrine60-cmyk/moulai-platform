// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// @ts-check
/** Device-local schedule before paint; manual choice lasts only this opening. */
(() => {
  /** @typedef {'light' | 'dark'} Theme */
  /** @typedef {Readonly<{theme: Theme, preference: Theme, manual: boolean}>} Snapshot */
  const configuration = document.getElementById('moulai-appearance-schedule');
  if (!configuration?.textContent)
    throw new Error('Appearance schedule is required');
  /** @type {Readonly<{dayStartsAt: string, nightStartsAt: string, status: string}>} */
  const schedule = Object.freeze(JSON.parse(configuration.textContent));
  /** @param {string} value @returns {number} */
  const minuteOfDay = (value) =>
    Number(value.slice(0, 2)) * 60 + Number(value.slice(3, 5));
  const start = minuteOfDay(schedule.dayStartsAt);
  const end = minuteOfDay(schedule.nightStartsAt);
  if (
    ![schedule.dayStartsAt, schedule.nightStartsAt].every((v) =>
      /^([01]\d|2[0-3]):[0-5]\d$/.test(v),
    ) ||
    start === end
  )
    throw new Error('Invalid appearance schedule');
  /** @type {Theme | null} */
  let manual = null;
  /** @type {Set<() => void>} */
  const subscribers = new Set();
  /** Device hours ignore restaurant zones, OS preference and stored choices. @returns {Theme} */
  function scheduledTheme() {
    const now = new Date();
    const minutes = now.getHours() * 60 + now.getMinutes();
    const day =
      start < end
        ? minutes >= start && minutes < end
        : minutes >= start || minutes < end;
    return day ? 'light' : 'dark';
  }
  /** @type {Snapshot} */
  let snapshot = Object.freeze({
    theme: scheduledTheme(),
    preference: scheduledTheme(),
    manual: false,
  });
  /** Keep React snapshots stable without changing foreground opacity. @returns {void} */
  function apply() {
    const theme = manual ?? scheduledTheme();
    const changed =
      theme !== snapshot.theme || snapshot.manual !== (manual !== null);
    if (changed)
      snapshot = Object.freeze({
        theme,
        preference: theme,
        manual: manual !== null,
      });
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    const meta = document.querySelector('meta[name="theme-color"]');
    const background = window
      .getComputedStyle(document.documentElement)
      .getPropertyValue('--surface-page')
      .trim();
    if (meta && background) meta.setAttribute('content', background);
    if (changed) subscribers.forEach((listener) => listener());
  }
  /** Never persist a manual choice to another opening. @param {Theme} value @returns {void} */
  function choose(value) {
    if (value !== 'light' && value !== 'dark')
      throw new TypeError('Invalid theme preference');
    manual = value;
    apply();
  }
  /** Follow clock boundaries until manually overridden. @returns {void} */
  function tick() {
    apply();
    window.setTimeout(tick, 60000 - (Date.now() % 60000));
  }
  window.setTimeout(tick, 60000 - (Date.now() % 60000));
  document.addEventListener('visibilitychange', apply);
  window.addEventListener('focus', apply);
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) manual = null;
    apply();
  });
  Object.defineProperty(window, 'moulaiTheme', {
    value: Object.freeze({
      getSnapshot: () => snapshot,
      /** @param {() => void} listener @returns {() => void} */
      subscribe: (listener) => {
        subscribers.add(listener);
        return () => {
          subscribers.delete(listener);
        };
      },
      choose,
      /** Compatibility hook: refresh the device clock only; business zones cannot override it. */
      setContextTimezone: apply,
      getSchedule: () => schedule,
    }),
  });
  apply();
  document.addEventListener('DOMContentLoaded', apply, { once: true });
})();
