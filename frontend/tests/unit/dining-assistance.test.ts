// MoulAI™ — local documentary answers and native voice are tested without provider/audio calls.
import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  safeHelpContext,
  explainLocally,
  boundedDocumentSelection,
  LocalHelpLimit,
} from '../../src/shared/dining/help/assistant';
import {
  GUIDE_VERSION,
  procedures,
} from '../../src/shared/dining/help/documentation';
import {
  LocalVoiceSession,
  type Recognizer,
  type RecognitionConstructor,
  type VoicePort,
} from '../../src/shared/dining/help/voice';
import {
  eventLabel,
  recordedChanges,
} from '../../src/features/dining/local/HistoryPanel';
import { assistance } from '../../src/shared/i18n/assistance';
import type { HistoryEvent } from '../../src/shared/dining/local/historyClient';
const base = {
  section: 'planning',
  role: 'employee',
  capabilities: ['read'],
  permissionsKnown: true,
  policyPresent: true,
  tableState: 'dirty',
  busy: false,
};
const ctx = () => safeHelpContext(base);
afterEach(() => vi.useRealTimers());
describe('versioned guidance without generation', () => {
  for (const [locale, question] of [
    ['fr', 'Pourquoi je ne peux pas installer ce client ?'],
    ['en', 'Why can I not seat this customer?'],
    ['ar', 'لماذا لا يمكن إجلاس هذا العميل؟'],
  ] as const)
    it('explains verified physical and permission facts ' + locale, () => {
      const result = explainLocally(question, ctx());
      expect(result.source).toBe('local-documentation');
      expect(result.topic).toBe('walkin');
      expect(result.notices).toContain('help.notVacant');
      expect(result.notices).toContain('help.missingService');
      expect(
        procedures.find((p) => p.id === result.topic)!.copy[locale].steps
          .length,
      ).toBeGreaterThan(2);
    });
  it('asks rather than guessing ambiguous intent or selected table', () => {
    expect(explainLocally('Comment confirmer ?', ctx()).clarification).toBe(
      true,
    );
    expect(explainLocally('réservation et paiement', ctx()).clarification).toBe(
      true,
    );
    const result = explainLocally(
      'install',
      safeHelpContext({ ...base, tableState: null }),
    );
    expect(result.clarification).toBe(true);
    expect(result.notices).toContain('help.chooseTable');
  });
  it('does not infer a missing permission from unloaded authority or certify availability', () => {
    expect(
      explainLocally(
        'install',
        safeHelpContext({ ...base, permissionsKnown: false }),
      ).notices,
    ).not.toContain('help.missingService');
    const result = explainLocally(
      'install',
      safeHelpContext({
        ...base,
        tableState: 'available',
        capabilities: ['service'],
      }),
    );
    expect(result.notices).toContain('help.cannotCertify');
    expect(result.notices).not.toContain('help.missingService');
  });
  it('uses only an allowlisted server error and omits raw context and credentials', () => {
    const supplied = {
      ...base,
      errorCode: 'dining_verified_matching_receipt_required',
      password: 'private',
      token: 'private',
      customer: 'private',
      capabilities: ['read', 'private'],
    };
    const safe = safeHelpContext(supplied);
    expect(JSON.stringify(safe)).not.toContain('private');
    expect(explainLocally('erreur', safe).notices).toContain('help.errReceipt');
    expect(
      safeHelpContext({ ...base, errorCode: 'private stack' }).errorCode,
    ).toBeNull();
    expect(
      safeHelpContext({
        ...base,
        control: {
          labelKey: 'private',
          type: 'text',
          required: true,
          disabled: false,
          invalid: false,
        },
      }).control,
    ).toBeNull();
  });
  it('has a full procedure contract in all three languages', () => {
    for (const guide of procedures)
      for (const locale of ['fr', 'en', 'ar'] as const) {
        const p = guide.copy[locale];
        for (const value of [
          p.title,
          p.who,
          p.requires,
          p.result,
          p.blocked,
          ...p.steps,
        ])
          expect(value.length).toBeGreaterThan(10);
      }
    expect(Object.keys(assistance.fr)).toEqual(Object.keys(assistance.en));
    expect(Object.keys(assistance.fr)).toEqual(Object.keys(assistance.ar));
  });
  it('never invokes a provider by default', async () => {
    const fallback = explainLocally('install', ctx());
    const response = await boundedDocumentSelection({
      current: ctx(),
      fallback,
    });
    expect(response.plan).toBe(fallback);
    expect(response.selectionUsed).toBe(false);
  });
  it('accepts only bounded version-matched document selections from an in-process fake', async () => {
    const select = vi.fn(async () => ({
      version: GUIDE_VERSION,
      topics: ['walkin'],
      clarify: false,
    }));
    const response = await boundedDocumentSelection({
      selector: { select },
      current: ctx(),
      fallback: explainLocally('install', ctx()),
    });
    expect(response.selectionUsed).toBe(true);
    expect(select).toHaveBeenCalledTimes(1);
    expect(select.mock.calls[0]).toBeDefined();
    expect(response.plan.source).toBe('local-documentation');
  });
  for (const result of [
    { version: 'old', topics: ['walkin'], clarify: false },
    { version: GUIDE_VERSION, topics: ['future-feature'], clarify: false },
    {
      version: GUIDE_VERSION,
      topics: ['walkin'],
      clarify: false,
      action: 'confirm_payment',
    },
    'invented diagnosis',
  ])
    it(
      'rejects invented features, actions and malformed selections ' +
        JSON.stringify(result),
      async () => {
        const response = await boundedDocumentSelection({
          selector: { select: async () => result },
          current: ctx(),
          fallback: explainLocally('install', ctx()),
        });
        expect(response.fallback).toBe(true);
        expect(response.selectionUsed).toBe(false);
      },
    );
  it('times out once and falls back without retry', async () => {
    vi.useFakeTimers();
    const select = vi.fn(() => new Promise<never>(() => {}));
    const response = boundedDocumentSelection({
      selector: { select },
      current: ctx(),
      fallback: explainLocally('install', ctx()),
      timeoutMs: 10,
    });
    await vi.advanceTimersByTimeAsync(11);
    expect((await response).fallback).toBe(true);
    expect(select).toHaveBeenCalledTimes(1);
  });
  it('limits documentary interactions per minute and opening', () => {
    const limit = new LocalHelpLimit();
    for (let i = 0; i < 10; i++) expect(limit.admit(0)).toBe(true);
    expect(limit.admit(1)).toBe(false);
    for (let round = 1; round < 3; round++)
      for (let i = 0; i < 10; i++)
        expect(limit.admit(round * 60001)).toBe(true);
    expect(limit.admit(999999)).toBe(false);
  });
});
describe('recorded business journal', () => {
  const row: HistoryEvent = {
    id: 1,
    kind: 'reference.created',
    occurred_at: '2026-11-05T10:00:00Z',
    request_id: null,
    author_key: 'kind:unknown',
    author_name: null,
    author_name_source: null,
    details: { kind: 'zone' },
  };
  for (const locale of ['fr', 'en', 'ar'] as const)
    it('translates exact event meaning ' + locale, () => {
      const t = (key: string, options?: { defaultValue: string }) =>
        assistance[locale][key as keyof typeof assistance.fr] ??
        options?.defaultValue ??
        key;
      expect(eventLabel(row, t)).toBe(
        assistance[locale]['audit.reference.zone'],
      );
      expect(eventLabel({ ...row, kind: 'unknown.future' }, t)).toBe(
        assistance[locale]['audit.unknown'],
      );
    });
  it('retains actual before and after values without manufacturing absent history', () => {
    expect(
      recordedChanges({
        ...row,
        details: { previous_expected_end: 'a', expected_end: 'b' },
      }),
    ).toEqual([{ field: 'expected_end', before: 'a', after: 'b' }]);
    expect(recordedChanges({ ...row, details: { active: false } })).toEqual([
      { field: 'active', before: undefined, after: false },
    ]);
    expect(recordedChanges(row)).toEqual([]);
  });
});
describe('optional local-only voice with fake device', () => {
  const port = (): VoicePort => ({
    voices: () => [{ uri: 'remote', lang: 'fr-FR', local: false }],
    play: vi.fn(() => ({ pause: vi.fn(), resume: vi.fn(), stop: vi.fn() })),
  });
  it('does not speak on construction and refuses remote-only voices', () => {
    const p = port(),
      status = vi.fn();
    const voice = new LocalVoiceSession(p, 'fr', status, vi.fn());
    expect(p.play).not.toHaveBeenCalled();
    expect(voice.canRead()).toBe(false);
    expect(voice.read('bonjour')).toBe(false);
    expect(p.play).not.toHaveBeenCalled();
  });
  it('reads only local matching language and supports pause, resume and close', () => {
    const p = port();
    p.voices = () => [{ uri: 'local', lang: 'fr-FR', local: true }];
    const controls = { pause: vi.fn(), resume: vi.fn(), stop: vi.fn() };
    p.play = vi.fn(() => controls);
    const voice = new LocalVoiceSession(p, 'fr', vi.fn(), vi.fn());
    expect(voice.read('Bonjour')).toBe(true);
    voice.pause();
    voice.resume();
    voice.close();
    expect(controls.pause).toHaveBeenCalledOnce();
    expect(controls.resume).toHaveBeenCalledOnce();
    expect(controls.stop).toHaveBeenCalledOnce();
  });
  it('blocks recognition without explicit installed-local support', async () => {
    const p = port(),
      voice = new LocalVoiceSession(p, 'ar', vi.fn(), vi.fn());
    expect(voice.startMicrophone()).toBe(false);
    expect(await voice.checkMicrophone()).toBe(false);
  });
  function microphone(status = 'available') {
    const devices: Recognizer[] = [];
    class LocalRecognition implements Recognizer {
      static available = vi.fn(async () => status);
      declare processLocally: boolean;
      lang = '';
      continuous = false;
      interimResults = false;
      maxAlternatives = 1;
      onresult: Recognizer['onresult'] = null;
      onerror: Recognizer['onerror'] = null;
      onend: Recognizer['onend'] = null;
      start = vi.fn();
      stop = vi.fn();
      abort = vi.fn();
      constructor() {
        devices.push(this);
      }
    }
    Object.defineProperty(LocalRecognition.prototype, 'processLocally', {
      value: false,
      writable: true,
    });
    const p = port();
    p.recognition = LocalRecognition as RecognitionConstructor;
    return { p, devices, LocalRecognition };
  }
  it('checks installed packs without starting; explicit start creates editable text only', async () => {
    const { p, devices, LocalRecognition } = microphone();
    const transcript = vi.fn();
    const voice = new LocalVoiceSession(p, 'ar', vi.fn(), transcript);
    expect(await voice.checkMicrophone()).toBe(true);
    expect(devices).toHaveLength(0);
    expect(LocalRecognition.available).toHaveBeenCalledWith({
      langs: ['ar-SA'],
      processLocally: true,
      quality: 'dictation',
    });
    expect(voice.startMicrophone()).toBe(true);
    expect(devices[0]!.processLocally).toBe(true);
    devices[0]!.onresult?.({ results: [[{ transcript: 'نص قابل للتعديل' }]] });
    expect(transcript).toHaveBeenCalledWith('نص قابل للتعديل');
    const stale = devices[0]!.onresult;
    voice.close();
    stale?.({ results: [[{ transcript: 'late' }]] });
    expect(transcript).toHaveBeenCalledTimes(1);
    expect(devices[0]!.abort).toHaveBeenCalledOnce();
  });
  it('refuses unavailable packs and handles permission denial without retry', async () => {
    const unavailable = microphone('downloadable');
    const blocked = new LocalVoiceSession(
      unavailable.p,
      'en',
      vi.fn(),
      vi.fn(),
    );
    expect(await blocked.checkMicrophone()).toBe(false);
    expect(blocked.startMicrophone()).toBe(false);
    expect(unavailable.devices).toHaveLength(0);
    const { p, devices } = microphone();
    const status = vi.fn();
    const voice = new LocalVoiceSession(p, 'fr', status, vi.fn());
    await voice.checkMicrophone();
    voice.startMicrophone();
    devices[0]!.onerror?.();
    expect(status).toHaveBeenLastCalledWith('unavailable');
    expect(devices[0]!.start).toHaveBeenCalledOnce();
  });
});
