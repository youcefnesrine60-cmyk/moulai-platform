// MoulAI™ — primary artwork changes only the entry controls, never help semantics or network activity.
import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import i18n from '../../src/shared/i18n';
import { AssistanceLaunchers } from '../../src/shared/ui/AssistanceLaunchers';
import { AccessHelp } from '../../src/features/access/AccessHelp';

describe.each(['fr', 'en', 'ar'] as const)(
  'original primary artwork %s',
  (locale) => {
    it('keeps distinct native controls with original images, names and translated tooltips', async () => {
      await i18n.changeLanguage(locale);
      const help = vi.fn(),
        assistant = vi.fn();
      render(<AssistanceLaunchers onHelp={help} onAssistant={assistant} />);
      const nav = screen.getByRole('navigation');
      expect(nav).toHaveAttribute('dir', locale === 'ar' ? 'rtl' : 'ltr');
      const buttons = within(nav).getAllByRole('button');
      expect(buttons).toHaveLength(2);
      for (const [index, name] of [
        'Icon-help-MoulAI(2).png',
        'Icon-Assistant-MoulAI(2).png',
      ].entries()) {
        const button = buttons[index]!;
        expect(button.textContent).toBe('');
        const img = button.querySelector('img')!;
        expect(img).toHaveAttribute('src', '/brand/' + name);
        expect(img).toHaveAttribute('width', '48');
        expect(img).toHaveAttribute('height', '48');
        expect(img).toHaveAttribute('alt', '');
        expect(button).toHaveAccessibleName(
          i18n.t(index === 0 ? 'help.open' : 'help.assistant'),
        );
        fireEvent.click(button);
      }
      expect(help).toHaveBeenCalledOnce();
      expect(assistant).toHaveBeenCalledOnce();
      expect(buttons[1]).toHaveAccessibleDescription(
        expect.stringContaining(i18n.t('help.pendingShort')),
      );
      expect(
        screen
          .getAllByRole('tooltip', { hidden: true })
          .map((x) => x.textContent),
      ).toEqual([i18n.t('help.tooltip'), i18n.t('help.assistant')]);
    });
    it('still opens documentary help and a truthful unavailable assistant without a provider call', async () => {
      await i18n.changeLanguage(locale);
      const network = vi.spyOn(globalThis, 'fetch');
      render(<AccessHelp operational />);
      fireEvent.click(
        screen.getByRole('button', { name: i18n.t('help.open') }),
      );
      expect(screen.getByRole('dialog')).toHaveTextContent(
        i18n.t('assist.docs'),
      );
      fireEvent.click(
        screen.getByRole('button', { name: i18n.t('help.close') }),
      );
      fireEvent.click(
        screen.getByRole('button', { name: i18n.t('help.assistant') }),
      );
      expect(screen.getByRole('dialog')).toHaveTextContent(
        i18n.t('assist.unavailable'),
      );
      expect(screen.getByRole('textbox')).toBeVisible();
      expect(network).not.toHaveBeenCalled();
      network.mockRestore();
    });
  },
);
