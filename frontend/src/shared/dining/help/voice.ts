// MoulAI™ — optional native voice, strictly local-service voices and on-device recognition.
import type { Locale } from '../../access/contracts';
export interface VoiceChoice {
  uri: string;
  lang: string;
  local: boolean;
}
export interface Playback {
  pause(): void;
  resume(): void;
  stop(): void;
}
export interface Recognizer {
  processLocally: boolean;
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult:
    | ((event: {
        results: ArrayLike<ArrayLike<{ transcript: string }>>;
      }) => void)
    | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
export interface RecognitionConstructor {
  new (): Recognizer;
  prototype: { processLocally?: boolean };
  available?(options: {
    langs: string[];
    processLocally: true;
    quality: 'dictation';
  }): Promise<string>;
}
export interface VoicePort {
  voices(): readonly VoiceChoice[];
  play(
    text: string,
    voice: VoiceChoice,
    onEnd: () => void,
    onError: () => void,
  ): Playback;
  recognition?: RecognitionConstructor;
}
export type VoiceState =
  'idle' | 'speaking' | 'paused' | 'listening' | 'unavailable';
const speechLanguages: Record<Locale, string> = {
  fr: 'fr-FR',
  en: 'en-GB',
  ar: 'ar-SA',
};

/** Reading metadata does not speak, request microphone permission or install a pack. */
export function browserVoicePort(): VoicePort {
  const browser = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  const recognition =
    browser.SpeechRecognition ?? browser.webkitSpeechRecognition;
  return {
    voices: () =>
      window.speechSynthesis?.getVoices().map((voice) => ({
        uri: voice.voiceURI,
        lang: voice.lang,
        local: voice.localService === true,
      })) ?? [],
    play: (text, choice, onEnd, onError) => {
      const synth = window.speechSynthesis;
      const voice = synth
        ?.getVoices()
        .find(
          (item) => item.voiceURI === choice.uri && item.localService === true,
        );
      if (!synth || !voice || typeof SpeechSynthesisUtterance === 'undefined')
        throw new Error('Local voice unavailable');
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.voice = voice;
      utterance.lang = voice.lang;
      utterance.onend = onEnd;
      utterance.onerror = onError;
      synth.speak(utterance);
      return {
        pause: () => synth.pause(),
        resume: () => synth.resume(),
        stop: () => {
          utterance.onend = null;
          utterance.onerror = null;
          synth.cancel();
        },
      };
    },
    ...(recognition ? { recognition } : {}),
  };
}

/** Own only this panel's ephemeral speech. There is no audio recording, upload or persistence API. */
export class LocalVoiceSession {
  private playback: Playback | null = null;
  private recognition: Recognizer | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private epoch = 0;
  private microphoneReady = false;
  private checking = 0;
  constructor(
    private readonly port: VoicePort,
    private readonly locale: Locale,
    private readonly status: (value: VoiceState) => void,
    private readonly transcript: (value: string) => void,
  ) {}
  canRead(): boolean {
    return this.port
      .voices()
      .some(
        (voice) =>
          voice.local && voice.lang.toLowerCase().startsWith(this.locale),
      );
  }
  read(text: string): boolean {
    this.stop();
    const voice = this.port
      .voices()
      .find(
        (voice) =>
          voice.local && voice.lang.toLowerCase().startsWith(this.locale),
      );
    if (!voice || !text.trim() || text.length > 6000) {
      this.status('unavailable');
      return false;
    }
    const epoch = this.epoch;
    try {
      this.playback = this.port.play(
        text,
        voice,
        () => {
          if (epoch === this.epoch) this.stop();
        },
        () => {
          if (epoch === this.epoch) {
            this.stop();
            this.status('unavailable');
          }
        },
      );
      this.status('speaking');
      this.timer = setTimeout(() => this.stop(), 120000);
      return true;
    } catch {
      this.status('unavailable');
      return false;
    }
  }
  pause(): void {
    if (this.playback) {
      this.playback.pause();
      this.status('paused');
    }
  }
  resume(): void {
    if (this.playback) {
      this.playback.resume();
      this.status('speaking');
    }
  }
  async checkMicrophone(): Promise<boolean> {
    const Constructor = this.port.recognition;
    const check = ++this.checking;
    this.microphoneReady = false;
    if (
      !Constructor?.available ||
      !('processLocally' in Constructor.prototype)
    ) {
      this.status('unavailable');
      return false;
    }
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      const result = await Promise.race([
        Constructor.available({
          langs: [speechLanguages[this.locale]],
          processLocally: true,
          quality: 'dictation',
        }),
        new Promise<string>((resolve) => {
          timer = setTimeout(() => resolve('unavailable'), 3000);
        }),
      ]);
      if (check !== this.checking) return false;
      this.microphoneReady = result === 'available';
      if (!this.microphoneReady) this.status('unavailable');
      return this.microphoneReady;
    } catch {
      if (check === this.checking) this.status('unavailable');
      return false;
    } finally {
      if (timer) clearTimeout(timer);
    }
  }
  startMicrophone(): boolean {
    if (!this.microphoneReady || !this.port.recognition) {
      this.status('unavailable');
      return false;
    }
    this.stop();
    const epoch = this.epoch;
    try {
      const recognition = new this.port.recognition();
      recognition.processLocally = true;
      if (recognition.processLocally !== true)
        throw new Error('Local mode not enforced');
      recognition.lang = speechLanguages[this.locale];
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      recognition.onresult = (event) => {
        if (epoch !== this.epoch) return;
        const text = event.results[0]?.[0]?.transcript;
        if (typeof text === 'string' && text.trim() && text.length <= 600)
          this.transcript(text.trim());
      };
      recognition.onerror = () => {
        if (epoch === this.epoch) {
          this.stop();
          this.status('unavailable');
        }
      };
      recognition.onend = () => {
        if (epoch === this.epoch) this.stop();
      };
      this.recognition = recognition;
      recognition.start();
      this.status('listening');
      this.timer = setTimeout(() => this.stop(), 20000);
      return true;
    } catch {
      this.stop();
      this.status('unavailable');
      return false;
    }
  }
  stop(): void {
    this.epoch++;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    const playback = this.playback;
    this.playback = null;
    try {
      playback?.stop();
    } catch {
      /* Native cancellation can race an ended utterance; still release our session. */
    }
    if (this.recognition) {
      this.recognition.onresult = null;
      this.recognition.onerror = null;
      this.recognition.onend = null;
      const recognition = this.recognition;
      this.recognition = null;
      try {
        recognition.abort();
      } catch {
        /* Failed native start may already have released its microphone. */
      }
    }
    this.status('idle');
  }
  close(): void {
    this.checking++;
    this.microphoneReady = false;
    this.stop();
  }
}
