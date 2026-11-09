// MoulAI™ — local documentation only. Conversational and voice integration is explicitly pending.
import { useEffect, useRef, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../shared/ui/primitives';
import { AssistanceLaunchers } from '../../../shared/ui/AssistanceLaunchers';
import {
  GUIDE_VERSION,
  procedures,
  procedure,
  topicForOperation,
  topicForSection,
  type Topic,
} from '../../../shared/dining/help/documentation';
import {
  readSelectedElement,
  elementRule,
  type SelectedElement,
} from '../../../shared/dining/help/elements';
import {
  HELP_EVENT,
  type HelpRequest,
} from '../../../shared/dining/help/requests';
import styles from './assistance.module.css';
import { VoiceControls } from './VoiceControls';
import {
  AssistantConversation,
  useConversationDraft,
} from './AssistantConversation';
interface Props {
  operational?: boolean;
  section: string;
  role: string;
  capabilities: readonly string[];
  permissionsKnown: boolean;
  policyPresent: boolean | null;
  tables: readonly { id: number; code: string; physical_state: string }[];
  selectedTable: number | null;
  busy: boolean;
  errorCode: string | null;
}
const operations = new Set(procedures.flatMap((item) => item.operations));
export function HelpDesk(props: Props) {
  const [conversation, setConversation] = useConversationDraft();
  const { t, i18n } = useTranslation(),
    locale =
      i18n.language === 'ar' ? 'ar' : i18n.language === 'en' ? 'en' : 'fr';
  const [open, setOpen] = useState(false),
    [mode, setMode] = useState<'guide' | 'assistant'>('guide'),
    [topic, setTopic] = useState<Topic>(topicForSection(props.section)),
    [operation, setOperation] = useState<string | null>(null),
    [control, setControl] = useState<SelectedElement | null>(null),
    [elementMode, setElementMode] = useState(false),
    [notice, setNotice] = useState<string | null>(null);
  const selectedId = useRef<string | undefined>(undefined),
    restore = useRef<HTMLElement | null>(null),
    pending = useRef<HTMLElement | null>(null),
    highlight = useRef<HTMLElement | null>(null),
    timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    selectedId.current = undefined;
    setControl(null);
    setElementMode(false);
  }, [props.section]);
  const chooseElement = (id: string | undefined) => {
    const item = readSelectedElement(id);
    selectedId.current = item ? id : undefined;
    setControl(item);
    return item;
  };
  const openHelp = (request: HelpRequest) => {
    restore.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    let op =
      request.operation && operations.has(request.operation)
        ? request.operation
        : null;
    if (request.field) {
      const selected = chooseElement(request.elementId);
      op = selected?.operation ?? op;
    }
    setElementMode(request.field === true);
    setMode(request.mode);
    setOperation(op);
    setTopic(
      op
        ? topicForOperation(op)
        : request.field
          ? 'start'
          : topicForSection(props.section),
    );
    setNotice(null);
    setOpen(true);
  };
  const openRef = useRef(openHelp);
  openRef.current = openHelp;
  useEffect(() => {
    const listen = (event: Event) => {
      const detail = (event as CustomEvent<unknown>).detail;
      if (
        !detail ||
        typeof detail !== 'object' ||
        !('mode' in detail) ||
        !['guide', 'assistant'].includes(String(detail.mode))
      )
        return;
      openRef.current({
        mode: detail.mode as HelpRequest['mode'],
        ...('operation' in detail && typeof detail.operation === 'string'
          ? { operation: detail.operation }
          : {}),
        ...('field' in detail && detail.field === true ? { field: true } : {}),
        ...('elementId' in detail && typeof detail.elementId === 'string'
          ? { elementId: detail.elementId }
          : {}),
      });
    };
    window.addEventListener(HELP_EVENT, listen);
    return () => {
      window.removeEventListener(HELP_EVENT, listen);
      if (timer.current) clearTimeout(timer.current);
      highlight.current?.classList.remove('moulai-guided-focus');
    };
  }, []);
  const item = procedure(topic, props.operational === true),
    copy = item.copy[locale],
    rule = control ? elementRule(control) : null;
  const guide = () => {
    const op =
      operation && item.operations.includes(operation)
        ? operation
        : item.operations[0];
    const form = op
      ? document.querySelector<HTMLFormElement>(`form[data-operation="${op}"]`)
      : null;
    const target =
      form?.querySelector<HTMLElement>(
        'input:invalid:not(:disabled):not([type="password"]):not([type="file"]),select:invalid:not(:disabled),textarea:invalid:not(:disabled)',
      ) ??
      form?.querySelector<HTMLElement>(
        'input:not(:disabled):not([type="hidden"]):not([type="password"]):not([type="file"]),select:not(:disabled),textarea:not(:disabled)',
      );
    if (!target) {
      setNotice('help.noTarget');
      return;
    }
    const details = form?.closest('details');
    if (details) details.open = true;
    highlight.current?.classList.remove('moulai-guided-focus');
    if (timer.current) clearTimeout(timer.current);
    target.classList.add('moulai-guided-focus');
    highlight.current = target;
    pending.current = target;
    timer.current = setTimeout(
      () => target.classList.remove('moulai-guided-focus'),
      8000,
    );
    setNotice('help.highlighted');
    setOpen(false);
  };
  const usage =
    control?.kind === 'button'
      ? control.action === 'session-open'
        ? 'element.sessionUse'
        : control.action === 'session-close'
          ? 'element.closeUse'
          : 'element.use_button'
      : control?.kind === 'select'
        ? 'element.use_select'
        : control?.kind === 'toggle'
          ? 'element.use_toggle'
          : control?.kind === 'choice' || control?.kind === 'group'
            ? 'element.use_choice'
            : 'element.use_field';
  return (
    <>
      <AssistanceLaunchers
        expanded={open ? mode : null}
        onHelp={() => openHelp({ mode: 'guide' })}
        onAssistant={() => openHelp({ mode: 'assistant' })}
      />
      {!open && notice === 'help.highlighted' && (
        <p className={styles.guidedNotice} role="status">
          {t(notice)}
        </p>
      )}
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className={styles.overlay} />
          <Dialog.Content
            id="dining-element-help"
            data-assistance-panel
            className={styles.panel}
            dir={locale === 'ar' ? 'rtl' : 'ltr'}
            onCloseAutoFocus={(event) => {
              event.preventDefault();
              const node = pending.current ?? restore.current;
              pending.current = null;
              if (node?.isConnected) {
                node.focus();
                if (node === highlight.current)
                  node.scrollIntoView({ block: 'center' });
              }
            }}
          >
            <div className={styles.heading}>
              <Dialog.Title>
                {t(mode === 'assistant' ? 'help.assistant' : 'help.open')}
              </Dialog.Title>
              <Dialog.Close asChild>
                <Button type="button" variant="secondary">
                  {t('help.close')}
                </Button>
              </Dialog.Close>
            </div>
            <Dialog.Description>
              {t(mode === 'guide' ? 'help.local' : 'assist.unavailable')}{' '}
              {t('help.readonly')}
            </Dialog.Description>
            {mode === 'assistant' ? (
              <AssistantConversation
                state={conversation}
                setState={setConversation}
                screen={copy.title}
                onGuide={() => setMode('guide')}
              />
            ) : (
              <>
                <p className={styles.notice}>{t('help.remoteOff')}</p>
                <div className={styles.actions}>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      chooseElement(selectedId.current);
                      setElementMode(true);
                    }}
                  >
                    {t('help.fieldHelp')}
                  </Button>
                </div>
                {elementMode && (
                  <section
                    className={styles.box}
                    data-testid="element-explanation"
                  >
                    <h2>{t('help.control')}</h2>
                    {control ? (
                      <>
                        <p>
                          <strong>{t('d1.' + control.labelKey)}</strong> ·{' '}
                          {t('element.kind_' + control.kind)}
                        </p>
                        {rule ? (
                          <>
                            <h3>{t('element.role')}</h3>
                            <p>{t('element.rule.' + rule)}</p>
                            <h3>{t('element.use')}</h3>
                            <p>{t(usage)}</p>
                            {(control.kind === 'field' ||
                              control.kind === 'select') && (
                              <p>
                                {t(
                                  control.required
                                    ? 'help.required'
                                    : 'help.optional',
                                )}
                              </p>
                            )}
                            <h3>{t('help.requires')}</h3>
                            <p>{copy.requires}</p>
                            <p>{t('element.conditions')}</p>
                            {control.invalid && <p>{t('help.fieldInvalid')}</p>}
                            {control.disabled && (
                              <>
                                <h3>{t('help.blocked')}</h3>
                                <p>
                                  {t(
                                    control.disabledReason === 'busy'
                                      ? 'element.busy'
                                      : control.disabledReason ===
                                          'fixedReference'
                                        ? 'element.fixedReference'
                                        : 'element.disabled',
                                  )}
                                </p>
                              </>
                            )}
                          </>
                        ) : (
                          <p>{t('element.unavailable')}</p>
                        )}
                      </>
                    ) : (
                      <p>{t('help.noField')}</p>
                    )}
                  </section>
                )}
                <p>
                  {t('help.contextLabel')}:{' '}
                  {t(
                    'd1.section_' +
                      (props.section === 'unscoped'
                        ? 'planning'
                        : props.section),
                  )}{' '}
                  ·{' '}
                  {t(
                    'help.role_' +
                      (['owner', 'manager', 'employee'].includes(props.role)
                        ? props.role
                        : 'none'),
                  )}
                </p>
                <label className={styles.field}>
                  {t('help.topic')}
                  <select
                    aria-label={t('help.topic')}
                    value={topic}
                    onChange={(event) => {
                      setTopic(event.target.value as Topic);
                      setOperation(null);
                      setElementMode(false);
                      setNotice(null);
                    }}
                  >
                    {procedures.map((guide) => (
                      <option key={guide.id} value={guide.id}>
                        {guide.copy[locale].title}
                      </option>
                    ))}
                  </select>
                </label>
                {notice && (
                  <p className={styles.box} role="status">
                    {t(notice)}
                  </p>
                )}
                <article
                  className={styles.box}
                  data-guide-version={GUIDE_VERSION}
                >
                  <h2>{copy.title}</h2>
                  <h3>{t('help.who')}</h3>
                  <p>{copy.who}</p>
                  <h3>{t('help.requires')}</h3>
                  <p>{copy.requires}</p>
                  <h3>{t('help.steps')}</h3>
                  <ol>
                    {copy.steps.map((step, index) => (
                      <li key={index}>{step}</li>
                    ))}
                  </ol>
                  <h3>{t('help.result')}</h3>
                  <p>{copy.result}</p>
                  <h3>{t('help.blocked')}</h3>
                  <p>{copy.blocked}</p>
                  <Button type="button" variant="secondary" onClick={guide}>
                    {t('help.next')}
                  </Button>
                  <p className={styles.notice}>
                    {t('help.version')}: <bdi dir="ltr">{GUIDE_VERSION}</bdi>
                  </p>
                </article>
                <VoiceControls
                  mode="playback"
                  text={[
                    copy.title,
                    copy.who,
                    copy.requires,
                    ...copy.steps,
                    copy.result,
                    copy.blocked,
                  ].join('. ')}
                  locale={locale}
                  onTranscript={() => undefined}
                />
                <details className={styles.box}>
                  <summary>{t('audit.tech')}</summary>
                  <p>
                    <bdi dir="ltr">{GUIDE_VERSION}</bdi>
                  </p>
                  <ul>
                    {item.capabilities.map((cap) => (
                      <li key={cap}>
                        <bdi dir="ltr">{cap}</bdi>
                      </li>
                    ))}
                  </ul>
                  {props.errorCode &&
                    /^dining_[a-z0-9_]{1,100}$/.test(props.errorCode) && (
                      <p>
                        <bdi dir="ltr">{props.errorCode}</bdi>
                      </p>
                    )}
                </details>
              </>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
