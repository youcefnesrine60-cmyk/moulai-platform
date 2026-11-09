// MoulAI™ — conversation surface, deliberately disconnected from every provider and business API.
import {
  useState,
  useEffect,
  useRef,
  type Dispatch,
  type SetStateAction,
} from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../shared/ui/primitives';
import { VoiceControls } from './VoiceControls';
import styles from './assistance.module.css';

export interface ConversationDraft {
  question: string;
  questions: readonly string[];
  outcome: 'idle' | 'unavailable' | 'limit';
}
export const emptyConversation: ConversationDraft = {
  question: '',
  questions: [],
  outcome: 'idle',
};

/** State belongs to the page, so closing a dialog preserves the draft but stops voice. */
export function useConversationDraft() {
  return useState<ConversationDraft>(emptyConversation);
}

/** No adapter is installed: a submitted question gets an honest local status, never a fake AI reply. */
export function AssistantConversation({
  state,
  setState,
  screen,
  onGuide,
}: {
  state: ConversationDraft;
  setState: Dispatch<SetStateAction<ConversationDraft>>;
  screen: string;
  onGuide: () => void;
}) {
  const { t, i18n } = useTranslation();
  const body = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (body.current) body.current.scrollTop = body.current.scrollHeight;
  }, [state.questions]);
  const locale =
    i18n.language === 'ar' ? 'ar' : i18n.language === 'en' ? 'en' : 'fr';
  return (
    <section
      className={styles.conversation}
      data-testid="assistant-conversation"
    >
      <div ref={body} className={styles.conversationBody}>
        <p role="status" className={styles.notice}>
          {t('assist.unavailable')}
        </p>
        <details className={styles.box}>
          <summary>{t('assist.diagnosis')}</summary>
          <p>{t('assist.context', { screen })}</p>
          <p>{t('assist.docs')}</p>
          <p>{t('assist.connector')}</p>
          <p>{t('assist.billing')}</p>
          <p>{t('assist.voice')}</p>
          <p>{t('assist.privacy')}</p>
        </details>
        <Button type="button" variant="secondary" onClick={onGuide}>
          {t('help.guide')}
        </Button>
        <section aria-label={t('assist.history')} className={styles.messages}>
          {!state.questions.length && <p>{t('assist.empty')}</p>}
          {state.questions.map((question, index) => (
            <article key={index} className={styles.box}>
              <strong>{t('assist.you')}</strong>
              <p className={styles.question} dir="auto">
                {question}
              </p>
            </article>
          ))}
        </section>
        {state.outcome !== 'idle' && (
          <p role={state.outcome === 'limit' ? 'alert' : 'status'}>
            {t(state.outcome === 'limit' ? 'assist.limit' : 'assist.notSent')}
          </p>
        )}
        <div className={styles.actions}>
          <Button
            type="button"
            variant="secondary"
            disabled
            aria-describedby="assistant-no-reply"
          >
            {t('voice.listen')}
          </Button>
          <span id="assistant-no-reply">{t('assist.noReply')}</span>
        </div>
      </div>
      <form
        className={styles.composer}
        aria-label={t('help.assistant')}
        onSubmit={(event) => {
          event.preventDefault();
          if (!state.question.trim()) return;
          setState((previous) =>
            previous.questions.length >= 10
              ? { ...previous, outcome: 'limit' }
              : {
                  question: '',
                  questions: [...previous.questions, previous.question.trim()],
                  outcome: 'unavailable',
                },
          );
        }}
      >
        <label className={styles.field}>
          {t('assist.question')}
          <textarea
            maxLength={600}
            value={state.question}
            onChange={(event) =>
              setState((previous) => ({
                ...previous,
                question: event.target.value,
              }))
            }
          />
        </label>
        <Button type="submit" disabled={!state.question.trim()}>
          {t('assist.send')}
        </Button>
        <VoiceControls
          text=""
          mode="microphone"
          locale={locale}
          onTranscript={(question) =>
            setState((previous) => ({ ...previous, question }))
          }
        />
      </form>
    </section>
  );
}
