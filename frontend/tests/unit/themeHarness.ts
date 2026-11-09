// MoulAI™ — execute the real parser-blocking bootstrap with isolated device clocks.
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import type { ThemeStore } from '../../src/shared/theme';
export function bootTheme(
  instant = '2026-11-05T12:00:00Z',
  offset = 0,
  stored = 'dark',
) {
  let now = Date.parse(instant);
  const document =
    globalThis.document.implementation.createHTMLDocument('appearance');
  document.head.innerHTML = `<script id="moulai-appearance-schedule">${readFileSync('public/appearance-schedule.json', 'utf8')}</script>`;
  document.body.innerHTML = '<input id="draft" value="kept">';
  const events = new globalThis.window.EventTarget();
  const values = new Map([['moulai.theme', stored]]);
  const timers: (() => void)[] = [];
  class Clock extends Date {
    constructor(value?: string | number) {
      super(value ?? now);
    }
    static now() {
      return now;
    }
    getHours() {
      return new Date(this.getTime() + offset * 60000).getUTCHours();
    }
    getMinutes() {
      return new Date(this.getTime() + offset * 60000).getUTCMinutes();
    }
  }
  const window = {
    setTimeout: (callback: () => void) => timers.push(callback),
    localStorage: {
      getItem: (k: string) => values.get(k),
      setItem: (k: string, v: string) => values.set(k, v),
    },
    matchMedia: () => ({ matches: true }),
    getComputedStyle: () => ({ getPropertyValue: () => '' }),
    addEventListener: events.addEventListener.bind(events),
  };
  runInNewContext(readFileSync('public/theme-init.js', 'utf8'), {
    window,
    document,
    Date: Clock,
  });
  return {
    store: (window as unknown as { moulaiTheme: ThemeStore }).moulaiTheme,
    documentElement: document.documentElement,
    document,
    values,
    move: (instant: string) => {
      now = Date.parse(instant);
      document.dispatchEvent(new Event('visibilitychange'));
    },
    elapse: (instant: string) => {
      now = Date.parse(instant);
      const callback = timers.shift();
      if (!callback) throw new Error('Appearance timer missing');
      callback();
    },
    reopenFromCache: () => {
      const event = new globalThis.window.PageTransitionEvent('pageshow', {
        persisted: true,
      });
      events.dispatchEvent(event);
    },
  };
}
