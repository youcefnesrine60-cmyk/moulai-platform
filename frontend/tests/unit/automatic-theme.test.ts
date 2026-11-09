// MoulAI™ — approved device-local opening policy; no paid or remote service.
import { expect, it } from 'vitest';
import { bootTheme } from './themeHarness';
it.each([
  ['06:59:59', 'dark'],
  ['07:00:00', 'light'],
  ['18:59:59', 'light'],
  ['19:00:00', 'dark'],
  ['00:00:00', 'dark'],
])('applies %s before paint as %s', (time, expected) => {
  const { store, documentElement } = bootTheme('2026-11-05T' + time + 'Z');
  expect(store.getSnapshot().theme).toBe(expected);
  expect(documentElement.dataset.theme).toBe(expected);
  expect(documentElement.style.colorScheme).toBe(expected);
});
it('uses device-local hours across dates, not UTC, OS or restaurant time', () => {
  const { store } = bootTheme('2026-11-05T22:00:00Z', 540, 'dark');
  expect(store.getSnapshot().theme).toBe('light');
  store.setContextTimezone('Pacific/Honolulu', '300');
  expect(store.getSnapshot().theme).toBe('light');
});
it('crosses day/night boundaries while no manual override exists', () => {
  const { store, elapse } = bootTheme('2026-11-05T06:59:59Z');
  elapse('2026-11-05T07:00:00Z');
  expect(store.getSnapshot().theme).toBe('light');
  elapse('2026-11-05T18:59:59Z');
  expect(store.getSnapshot().theme).toBe('light');
  elapse('2026-11-05T19:00:00Z');
  expect(store.getSnapshot().theme).toBe('dark');
});
it('keeps manual choice and drafts for this opening only; next opening ignores old storage', () => {
  const { store, move, document, values, reopenFromCache } = bootTheme();
  store.choose('dark');
  move('2026-11-05T13:00:00Z');
  expect(store.getSnapshot().theme).toBe('dark');
  expect(document.querySelector<HTMLInputElement>('#draft')?.value).toBe(
    'kept',
  );
  expect(values.get('moulai.theme')).toBe('dark'); // unchanged legacy value, never written
  expect(
    bootTheme('2026-11-05T13:00:00Z', 0, 'dark').store.getSnapshot().theme,
  ).toBe('light');
  reopenFromCache();
  expect(store.getSnapshot().theme).toBe('light');
});
it.each(['auto', 'system', 'sepia'])(
  'rejects retired/unknown mode %s',
  (value) => {
    expect(() =>
      Reflect.apply(bootTheme().store.choose, undefined, [value]),
    ).toThrow('Invalid theme preference');
  },
);
