// MoulAI™ — separate local documentation and disconnected conversational surfaces.
import { useRef, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { useTranslation } from 'react-i18next';
import { Button } from '../../shared/ui/primitives';
import { AssistanceLaunchers } from '../../shared/ui/AssistanceLaunchers';
import {
  ACCESS_HELP_VERSION,
  accessDocumentation,
  accessScenarios,
  scenarioExplanation,
} from '../../shared/access/help';
import {
  AssistantConversation,
  useConversationDraft,
} from '../dining/local/AssistantConversation';
import styles from '../dining/local/assistance.module.css';
import { VoiceControls } from '../dining/local/VoiceControls';
import { SessionInformation } from '../../shared/ui/SessionInformation';
export function AccessHelp({
  operational = false,
  staging = false,
}: {
  operational?: boolean;
  staging?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const locale =
    i18n.language === 'ar' ? 'ar' : i18n.language === 'en' ? 'en' : 'fr';
  const [mode, setMode] = useState<'guide' | 'assistant'>('guide');
  const [open, setOpen] = useState(false);
  const returnFocus = useRef<HTMLElement | null>(null);
  const [conversation, setConversation] = useConversationDraft();
  function show(mode: 'guide' | 'assistant') {
    returnFocus.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    setMode(mode);
    setOpen(true);
  }
  return (
    <>
      <AssistanceLaunchers
        expanded={open ? mode : null}
        onHelp={() => show('guide')}
        onAssistant={() => show('assistant')}
      />
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className={styles.overlay} />
          <Dialog.Content
            className={styles.panel}
            dir={locale === 'ar' ? 'rtl' : 'ltr'}
            data-assistance-panel
            onCloseAutoFocus={(event) => {
              event.preventDefault();
              returnFocus.current?.focus();
            }}
          >
            <div className={styles.heading}>
              <Dialog.Title>
                {t(mode === 'guide' ? 'help.open' : 'help.assistant')}
              </Dialog.Title>
              <Dialog.Close asChild>
                <Button type="button" variant="secondary">
                  {t('help.close')}
                </Button>
              </Dialog.Close>
            </div>
            <Dialog.Description>
              {t(mode === 'guide' ? 'assist.docs' : 'assist.unavailable')}
            </Dialog.Description>
            {mode === 'assistant' ? (
              <AssistantConversation
                state={conversation}
                setState={setConversation}
                screen={t('access.title')}
                onGuide={() => setMode('guide')}
              />
            ) : (
              <>
                {operational && <SessionInformation local={!staging} />}
                <div data-guide-version={ACCESS_HELP_VERSION}>
                  {accessDocumentation(locale, operational).map((section) => (
                    <section key={section.title} className={styles.box}>
                      <h2>{section.title}</h2>
                      <p>{section.body}</p>
                    </section>
                  ))}
                </div>
                {!operational && (
                  <section className={styles.box}>
                    <h2>{t('options.details')}</h2>
                    <dl>
                      {Object.keys(accessScenarios).map((key) => (
                        <div key={key}>
                          <dt>{t('profile.' + key)}</dt>
                          <dd>{scenarioExplanation(key, locale)}</dd>
                        </div>
                      ))}
                    </dl>
                  </section>
                )}
                <VoiceControls
                  mode="playback"
                  locale={locale}
                  text={accessDocumentation(locale, operational)
                    .map((section) => section.title + '. ' + section.body)
                    .join('. ')}
                  onTranscript={() => undefined}
                />
                <p className={styles.notice}>
                  <bdi dir="ltr">{ACCESS_HELP_VERSION}</bdi>
                </p>
              </>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
