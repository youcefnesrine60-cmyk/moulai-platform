// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useSyncExternalStore } from 'react';

export type Theme = 'light' | 'dark';
export type ThemePreference = Theme | 'system';
export interface ThemeSnapshot {
  readonly theme: Theme;
  readonly preference: ThemePreference;
}
export interface ThemeStore {
  getSnapshot(): ThemeSnapshot;
  subscribe(listener: () => void): () => void;
  choose(preference: ThemePreference): void;
}
declare global {
  interface Window {
    readonly moulaiTheme: ThemeStore;
  }
}

/** Subscribe to the same pre-paint store; identity, query cache and drafts stay intact. */
export function useTheme(): ThemeSnapshot & { choose: ThemeStore['choose'] } {
  const store = window.moulaiTheme;
  if (!store) throw new Error('Appearance bootstrap is required.');
  const snapshot = useSyncExternalStore(store.subscribe, store.getSnapshot);
  return { ...snapshot, choose: store.choose };
}
