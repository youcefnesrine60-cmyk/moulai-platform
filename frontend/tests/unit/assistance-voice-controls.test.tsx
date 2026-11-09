// MoulAI™ — explicit user gestures only; native voice is replaced by an offline port.
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { expect, it, vi, beforeEach } from 'vitest';
import i18n from '../../src/shared/i18n';
import { VoiceControls } from '../../src/features/dining/local/VoiceControls';
import { assistance } from '../../src/shared/i18n/assistance';
const voice = vi.hoisted(() => ({
  read: vi.fn(),
  pause: vi.fn(),
  resume: vi.fn(),
  stop: vi.fn(),
  close: vi.fn(),
  check: vi.fn(),
  start: vi.fn(),
  status: (_state: string) => {},
  transcript: (_text: string) => {},
}));
vi.mock('../../src/shared/dining/help/voice', () => ({
  browserVoicePort: () => ({}),
  LocalVoiceSession: class {
    constructor(
      _port: unknown,
      _locale: string,
      status: (value: string) => void,
      transcript: (text: string) => void,
    ) {
      voice.status = status;
      voice.transcript = transcript;
    }
    canRead = () => true;
    read = (text: string) => {
      voice.read(text);
      voice.status('speaking');
    };
    pause = () => {
      voice.pause();
      voice.status('paused');
    };
    resume = () => {
      voice.resume();
      voice.status('speaking');
    };
    stop = voice.stop;
    close = voice.close;
    checkMicrophone = voice.check;
    startMicrophone = () => {
      voice.start();
      voice.status('listening');
    };
  },
}));
beforeEach(async () => {
  vi.clearAllMocks();
  voice.check.mockResolvedValue(true);
  await i18n.changeLanguage('fr');
});
it('reads only after a gesture and provides pause/resume/stop without microphone access', () => {
  const view = render(
    <VoiceControls
      text="Texte documentaire local"
      mode="playback"
      locale="fr"
      onTranscript={vi.fn()}
    />,
  );
  expect(voice.read).not.toHaveBeenCalled();
  expect(voice.check).not.toHaveBeenCalled();
  expect(voice.start).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole('button', { name: assistance.fr['voice.listen'] }),
  );
  expect(voice.read).toHaveBeenCalledWith('Texte documentaire local');
  fireEvent.click(
    screen.getByRole('button', { name: assistance.fr['voice.pause'] }),
  );
  fireEvent.click(
    screen.getByRole('button', { name: assistance.fr['voice.resume'] }),
  );
  fireEvent.click(
    screen.getByRole('button', { name: assistance.fr['voice.stop'] }),
  );
  expect(voice.pause).toHaveBeenCalledTimes(1);
  expect(voice.resume).toHaveBeenCalledTimes(1);
  view.unmount();
  expect(voice.close).toHaveBeenCalled();
});
it('requires a separate explicit local check and microphone gesture, and returns editable text only', async () => {
  const transcript = vi.fn();
  const view = render(
    <VoiceControls
      text=""
      mode="microphone"
      locale="fr"
      onTranscript={transcript}
    />,
  );
  const mic = screen.getByRole('button', { name: assistance.fr['voice.mic'] });
  expect(mic).toBeDisabled();
  expect(voice.check).not.toHaveBeenCalled();
  expect(voice.start).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole('button', { name: assistance.fr['voice.check'] }),
  );
  await waitFor(() => expect(mic).toBeEnabled());
  expect(voice.start).not.toHaveBeenCalled();
  fireEvent.click(mic);
  expect(voice.start).toHaveBeenCalledTimes(1);
  expect(
    screen.getByRole('button', { name: assistance.fr['voice.stopMic'] }),
  ).toBeVisible();
  voice.transcript('Texte synthétique à corriger');
  expect(transcript).toHaveBeenCalledWith('Texte synthétique à corriger');
  view.unmount();
  expect(voice.close).toHaveBeenCalled();
});
