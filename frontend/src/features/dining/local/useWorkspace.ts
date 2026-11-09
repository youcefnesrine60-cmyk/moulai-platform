// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  LocalDiningClient,
  LocalDiningError,
  readPlanning,
  type LocalScope,
  type LocalSession,
  type Snapshot,
  type Planning,
  type OperationResult,
} from '../../../shared/dining/local/client';

/** Fence reads and submissions by identity/scope; server permissions remain authoritative. */
export function useWorkspace({
  operational = false,
  organizationId,
  restaurantId,
}: {
  operational?: boolean;
  organizationId?: number;
  restaurantId?: number;
} = {}) {
  const api = useMemo(() => new LocalDiningClient(operational), [operational]);
  const [session, setSession] = useState<LocalSession | null>(null);
  const [actor, setActor] = useState('owner');
  const [scope, setScope] = useState<LocalScope | null>(null);
  const [data, setData] = useState<Snapshot | null>(null);
  const [planning, setPlanning] = useState<Planning | null>(null);
  const [planningError, setPlanningError] = useState(false);
  const [day, setDay] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [success, setSuccess] = useState(false);
  const [committedStale, setCommittedStale] = useState(false);
  const [result, setResult] = useState<OperationResult | null>(null);
  const [tab, setTab] = useState('planning');
  const epoch = useRef(0);
  const planningRead = useRef(0);
  const locked = useRef(false);
  const visibleDay = useRef('');
  const clear = () => {
    epoch.current++;
    planningRead.current++;
    visibleDay.current = '';
    setData(null);
    setPlanning(null);
    setPlanningError(false);
    setResult(null);
    setSuccess(false);
    setCommittedStale(false);
    setError(null);
    setDay('');
  };
  const fail = (value: unknown) => {
    setError(value);
    if (!(value instanceof LocalDiningError) || value.status >= 500) {
      setData(null);
      setPlanning(null);
    }
    if (
      value instanceof LocalDiningError &&
      [401, 403].includes(value.status)
    ) {
      epoch.current++;
      planningRead.current++;
      setData(null);
      setPlanning(null);
      setResult(null);
      if (value.status === 401) {
        window.moulaiTheme?.setContextTimezone?.(null, null);
        setSession(null);
        setScope(null);
      }
    }
  };
  const install = (incoming: LocalSession) => {
    const next = operational
      ? {
          ...incoming,
          scopes: incoming.scopes.filter(
            (scope) =>
              scope.organization_id === organizationId &&
              scope.restaurant_id === restaurantId,
          ),
        }
      : incoming;
    clear();
    setSession(next);
    setActor(next.actor);
    const candidate = new URLSearchParams(location.search).get('branch');
    setScope(
      next.scopes.find((row) => String(row.branch_id) === candidate) ?? null,
    );
    setTab('planning');
  };
  useEffect(() => {
    let current = true;
    const read = epoch.current;
    void api
      .currentSession()
      .then((next) => {
        if (current && read === epoch.current) install(next);
      })
      .catch((value) => {
        if (
          current &&
          read === epoch.current &&
          !(value instanceof LocalDiningError && value.status === 401)
        )
          fail(value);
        else if (
          current &&
          read === epoch.current &&
          value instanceof LocalDiningError &&
          value.status === 401
        )
          window.moulaiTheme?.setContextTimezone?.(null, null);
      });
    return () => {
      current = false;
      epoch.current++;
      planningRead.current++;
    };
  }, [api]);
  const loadPlanning = async (
    selected: LocalScope,
    value: string,
    expectedEpoch: number,
  ) => {
    const read = ++planningRead.current;
    setPlanning(null);
    setPlanningError(false);
    try {
      const next = await readPlanning(api, selected, value);
      if (expectedEpoch === epoch.current && read === planningRead.current)
        setPlanning(next);
    } catch (value) {
      if (expectedEpoch === epoch.current && read === planningRead.current) {
        setPlanningError(true);
        if (
          value instanceof LocalDiningError &&
          [401, 403].includes(value.status)
        )
          fail(value);
      }
    }
  };
  const refresh = async (
    selected: LocalScope,
    expectedEpoch = epoch.current,
  ) => {
    const next = await api.workspace(selected);
    if (expectedEpoch !== epoch.current) return;
    setData(next);
    window.moulaiTheme?.setContextTimezone?.(
      next.policy?.timezone ?? null,
      String(selected.branch_id),
    );
    if (next.policy) {
      const parts = new Intl.DateTimeFormat('en-CA', {
        timeZone: next.policy.timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }).formatToParts(new Date(next.server_time ?? Date.now()));
      const selectedDay =
        visibleDay.current ||
        ['year', 'month', 'day']
          .map((kind) => parts.find((part) => part.type === kind)?.value ?? '')
          .join('-');
      visibleDay.current = selectedDay;
      setDay(selectedDay);
      await loadPlanning(selected, selectedDay, expectedEpoch);
    } else {
      setPlanning(null);
    }
  };
  useEffect(() => {
    const read = epoch.current;
    if (scope)
      void refresh(scope, read).catch((value) => {
        if (read === epoch.current) fail(value);
      });
    return () => {
      epoch.current++;
      planningRead.current++;
    };
  }, [api, scope, session]);
  const exclusive = async (work: () => Promise<void>) => {
    if (locked.current) return;
    locked.current = true;
    setBusy(true);
    try {
      await work();
    } finally {
      locked.current = false;
      setBusy(false);
    }
  };
  const signIn = () =>
    exclusive(async () => {
      const selectedActor = actor;
      clear();
      window.moulaiTheme?.setContextTimezone?.(null, null);
      setSession(null);
      setScope(null);
      try {
        install(await api.signIn(selectedActor));
      } catch (value) {
        fail(value);
      }
    });
  const signOut = () =>
    exclusive(async () => {
      clear();
      window.moulaiTheme?.setContextTimezone?.(null, null);
      setSession(null);
      setScope(null);
      history.replaceState(null, '', location.pathname);
      try {
        await api.signOut();
      } catch (value) {
        fail(value);
      }
    });
  const changeScope = (value: string) => {
    if (locked.current) return;
    const next =
      session?.scopes.find((row) => String(row.branch_id) === value) ?? null;
    if (next?.branch_id === scope?.branch_id) return;
    clear();
    window.moulaiTheme?.setContextTimezone?.(null, null);
    setScope(next);
    setTab('planning');
    history.replaceState(
      null,
      '',
      next ? `?branch=${next.branch_id}` : location.pathname,
    );
  };
  const selectDay = (value: string) => {
    visibleDay.current = value;
    setDay(value);
    setPlanning(null);
    if (scope && value && data?.policy)
      void loadPlanning(scope, value, epoch.current);
  };
  const reload = () =>
    exclusive(async () => {
      setError(null);
      setSuccess(false);
      if (scope)
        try {
          await refresh(scope);
        } catch (value) {
          fail(value);
        }
    });
  const run = (work: () => Promise<OperationResult>) =>
    exclusive(async () => {
      setError(null);
      setSuccess(false);
      setCommittedStale(false);
      const read = epoch.current;
      let recorded: OperationResult;
      try {
        recorded = await work();
      } catch (value) {
        if (read === epoch.current) fail(value);
        return;
      }
      if (read !== epoch.current) return;
      setResult(recorded);
      try {
        if (scope) await refresh(scope, read);
        if (read === epoch.current) setSuccess(true);
      } catch (value) {
        if (read === epoch.current) {
          fail(value);
          setCommittedStale(true);
        }
      }
    });
  return {
    api,
    session,
    actor,
    setActor,
    scope,
    data,
    busy,
    error,
    success,
    committedStale,
    tab,
    setTab,
    day,
    planning,
    planningError,
    result,
    run,
    signIn,
    signOut,
    changeScope,
    selectDay,
    reload,
  };
}
