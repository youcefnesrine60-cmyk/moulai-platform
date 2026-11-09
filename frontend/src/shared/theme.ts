// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useSyncExternalStore } from 'react';

export type Theme = 'light' | 'dark';
export type ThemePreference = Theme;
export interface ThemeSnapshot {
  readonly theme: Theme;
  readonly preference: ThemePreference;
  readonly manual: boolean;
}
export interface ThemeStore {
  getSnapshot(): ThemeSnapshot;
  subscribe(listener: () => void): () => void;
  choose(preference: ThemePreference): void;
  setContextTimezone(timezone: string | null, context: string | null): void;
  getSchedule(): Readonly<{
    dayStartsAt: string;
    nightStartsAt: string;
    status: string;
  }> | null;
}
declare global {
  interface Window {
    readonly moulaiTheme: ThemeStore;
  }
}

/** Subscribe to the same pre-paint store; identity, query cache and drafts stay intact. */
export function useTheme(): ThemeSnapshot & {
  choose: ThemeStore['choose'];
  schedule: ReturnType<ThemeStore['getSchedule']>;
} {
  const store = window.moulaiTheme;
  if (!store) throw new Error('Appearance bootstrap is required.');
  const snapshot = useSyncExternalStore(store.subscribe, store.getSnapshot);
  return { ...snapshot, choose: store.choose, schedule: store.getSchedule() };
}
