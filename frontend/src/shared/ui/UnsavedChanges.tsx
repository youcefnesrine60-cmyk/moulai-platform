// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Only navigation is deferred. This registry stores flags, never form values or commands.
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useBlocker } from 'react-router';
import * as Dialog from '@radix-ui/react-dialog';
import { useTranslation } from 'react-i18next';
import { Button } from './primitives';
import styles from './ui.module.css';

type NavigationGuard = {
  update: (id: string, dirty: boolean) => void;
  navigate: (changeView: () => void) => void;
};
const Guard = createContext<NavigationGuard | null>(null);

/** A security-driven return to /access must never be vetoed by an unfinished form. */
export function UnsavedChangesProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [forms, setForms] = useState<ReadonlySet<string>>(new Set());
  const [pendingView, setPendingView] = useState<(() => void) | null>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const dirty = forms.size > 0;
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      dirty &&
      nextLocation.pathname !== '/access' &&
      (currentLocation.pathname !== nextLocation.pathname ||
        currentLocation.search !== nextLocation.search),
  );
  const update = useCallback(
    (id: string, changed: boolean) =>
      setForms((previous) => {
        if (previous.has(id) === changed) return previous;
        const next = new Set(previous);
        if (changed) next.add(id);
        else next.delete(id);
        return next;
      }),
    [],
  );
  const navigate = useCallback(
    (changeView: () => void) => {
      if (dirty) setPendingView(() => changeView);
      else changeView();
    },
    [dirty],
  );
  useEffect(() => {
    const expire = () => {
      setForms(new Set());
      setPendingView(null);
    };
    const unload = (event: BeforeUnloadEvent) => {
      if (dirty) {
        event.preventDefault();
        event.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', unload);
    window.addEventListener('moulai-session-expired', expire);
    return () => {
      window.removeEventListener('beforeunload', unload);
      window.removeEventListener('moulai-session-expired', expire);
    };
  }, [dirty]);
  const value = useMemo(() => ({ update, navigate }), [update, navigate]);
  const cancel = () => {
    setPendingView(null);
    if (blocker.state === 'blocked') blocker.reset();
  };
  return (
    <Guard.Provider value={value}>
      {children}
      <Dialog.Root
        open={pendingView !== null || blocker.state === 'blocked'}
        onOpenChange={(open) => {
          if (!open) cancel();
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className={styles.guardOverlay} />
          <Dialog.Content
            className={styles.guardDialog}
            aria-describedby="unsaved-description"
            onOpenAutoFocus={() => {
              returnFocus.current =
                document.activeElement instanceof HTMLElement
                  ? document.activeElement
                  : null;
            }}
            onCloseAutoFocus={(event) => {
              event.preventDefault();
              if (returnFocus.current?.isConnected)
                returnFocus.current.focus({ preventScroll: true });
              // A nested editor may already have restored its opener after explicit discard.
              // Do not steal that focus when the discarded field no longer exists.
              else if (document.activeElement === document.body)
                document
                  .getElementById('main-content')
                  ?.focus({ preventScroll: true });
            }}
          >
            <Dialog.Title>{t('quality.unsavedTitle')}</Dialog.Title>
            <Dialog.Description id="unsaved-description">
              {t('quality.unsavedBody')}
            </Dialog.Description>
            <div className={styles.stateActions}>
              <Button type="button" onClick={cancel}>
                {t('quality.stay')}
              </Button>
              <Button
                type="button"
                variant="danger"
                onClick={() => {
                  const next = pendingView;
                  setPendingView(null);
                  if (blocker.state === 'blocked') blocker.proceed();
                  else next?.();
                }}
              >
                {t('quality.leave')}
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </Guard.Provider>
  );
}

/** Clear only after confirmed persistence; a rejected or uncertain request stays dirty. */
export function useUnsavedChanges(dirty: boolean): void {
  const guard = useContext(Guard),
    id = useId(),
    update = guard?.update;
  useEffect(() => {
    update?.(id, dirty);
    return () => update?.(id, false);
  }, [id, dirty, update]);
}

/** In-place section and branch changes use the same explicit discard decision. */
export function useViewChange() {
  const guard = useContext(Guard);
  return guard?.navigate ?? ((changeView: () => void) => changeView());
}
