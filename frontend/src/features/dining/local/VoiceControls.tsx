// MoulAI™ — user gestures only. Unsupported on-device capabilities fail back to text.
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { Locale } from '../../../shared/access/contracts';
import { Button } from '../../../shared/ui/primitives';
import {
  browserVoicePort,
  LocalVoiceSession,
  type VoiceState,
} from '../../../shared/dining/help/voice';
import styles from './assistance.module.css';
export function VoiceControls({
  text,
  locale,
  onTranscript,
  mode = 'both',
}: {
  text: string;
  locale: Locale;
  onTranscript: (value: string) => void;
  mode?: 'both' | 'microphone' | 'playback';
}) {
  const { t } = useTranslation();
  const [state, setState] = useState<VoiceState>('idle'),
    [ready, setReady] = useState(false),
    [readable, setReadable] = useState(false),
    [checked, setChecked] = useState(false);
  const current = useRef<LocalVoiceSession | null>(null);
  const callback = useRef(onTranscript);
  callback.current = onTranscript;
  useEffect(() => {
    let alive = true;
    const voice = new LocalVoiceSession(
      browserVoicePort(),
      locale,
      (value) => {
        if (alive) setState(value);
      },
      (value) => {
        if (alive) callback.current(value);
      },
    );
    current.current = voice;
    setReady(false);
    setChecked(false);
    setState('idle');
    const voices = () => {
      if (alive) setReadable(voice.canRead());
    };
    voices();
    const hidden = () => {
      if (document.hidden) {
        voice.close();
        setReady(false);
      }
    };
    window.speechSynthesis?.addEventListener?.('voiceschanged', voices);
    document.addEventListener('visibilitychange', hidden);
    return () => {
      alive = false;
      voice.close();
      current.current = null;
      window.speechSynthesis?.removeEventListener?.('voiceschanged', voices);
      document.removeEventListener('visibilitychange', hidden);
    };
  }, [locale]);
  useEffect(() => {
    current.current?.stop();
  }, [text]);
  return (
    <section
      className={styles.voice}
      aria-label={t(mode === 'microphone' ? 'voice.mic' : 'voice.listen')}
    >
      {mode !== 'microphone' && <p>{t('voice.localOnly')}</p>}
      {mode !== 'microphone' && (
        <>
          <div className={styles.actions}>
            <Button
              type="button"
              variant="secondary"
              disabled={!readable || !text}
              onClick={() => current.current?.read(text)}
            >
              {t('voice.listen')}
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={state !== 'speaking' && state !== 'paused'}
              onClick={() =>
                state === 'paused'
                  ? current.current?.resume()
                  : current.current?.pause()
              }
            >
              {t(state === 'paused' ? 'voice.resume' : 'voice.pause')}
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={state !== 'speaking' && state !== 'paused'}
              onClick={() => current.current?.stop()}
            >
              {t('voice.stop')}
            </Button>
          </div>
          {!readable && <p>{t('voice.unavailable')}</p>}
        </>
      )}
      {mode !== 'playback' && (
        <>
          <div className={styles.actions}>
            <Button
              type="button"
              variant="secondary"
              disabled={state === 'listening'}
              onClick={() => {
                setChecked(true);
                const voice = current.current;
                void voice?.checkMicrophone().then((value) => {
                  if (current.current === voice) setReady(value);
                });
              }}
            >
              {t('voice.check')}
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={!ready}
              aria-pressed={state === 'listening'}
              onClick={() =>
                state === 'listening'
                  ? current.current?.stop()
                  : current.current?.startMicrophone()
              }
            >
              {t(state === 'listening' ? 'voice.stopMic' : 'voice.mic')}
            </Button>
          </div>
          {state === 'listening' && <p role="status">{t('voice.listening')}</p>}
          {checked && (
            <p role="status">
              {t(ready ? 'voice.ready' : 'voice.notAvailable')}
            </p>
          )}
          {state === 'unavailable' && <p role="status">{t('voice.failed')}</p>}
          <details>
            <summary>{t('assist.diagnosis')}</summary>
            <p>{t('assist.voice')}</p>
            <p>{t('voice.limit')}</p>
            <p>{t('voice.darija')}</p>
          </details>
        </>
      )}
    </section>
  );
}
