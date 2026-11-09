// MoulAI™ — explicit, typed documentary help; no conversational or voice service is active.
import { useState } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import i18n from '../../src/shared/i18n';
import { HelpDesk } from '../../src/features/dining/local/HelpDesk';
import { ElementHelp } from '../../src/features/dining/local/ElementHelp';
import { HelpLink } from '../../src/features/dining/local/HelpLink';
import { assistance } from '../../src/shared/i18n/assistance';
import { assistanceV2 } from '../../src/shared/i18n/assistanceV2';
import { d1Fr } from '../../src/shared/i18n/d1.fr';
import {
  readSelectedElement,
  elementRule,
} from '../../src/shared/dining/help/elements';
function Form({
  submit,
  disabled = false,
  unknown = false,
}: {
  submit: () => void;
  disabled?: boolean;
  unknown?: boolean;
}) {
  const [value, setValue] = useState('');
  return (
    <>
      <form
        data-operation="reference"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <label htmlFor="draft">Draft</label>
        <input
          id="draft"
          data-help-label={unknown ? 'description' : 'code'}
          name="draft"
          value={value}
          required
          onChange={(e) => setValue(e.target.value)}
        />
        <ElementHelp
          targetId="draft"
          labelKey={unknown ? 'description' : 'code'}
        />
        <label htmlFor="list">List</label>
        <select id="list" data-help-label="referenceKind">
          <option value="zone">Zone</option>
        </select>
        <ElementHelp targetId="list" labelKey="referenceKind" />
        <button
          id="save"
          data-help-label="save"
          type="submit"
          disabled={disabled}
        >
          Save
        </button>
        <ElementHelp targetId="save" labelKey="save" />
        <HelpLink operation="reference" />
      </form>
      <HelpDesk
        section="configuration"
        role="owner"
        capabilities={['read', 'configure']}
        permissionsKnown
        policyPresent
        tables={[]}
        selectedTable={null}
        busy={false}
        errorCode={null}
      />
    </>
  );
}
for (const locale of ['fr', 'en', 'ar'] as const) {
  it(
    'preserves draft and RTL while opening documentary help ' + locale,
    async () => {
      await i18n.changeLanguage(locale);
      const submit = vi.fn();
      render(<Form submit={submit} />);
      const input = screen.getByLabelText('Draft');
      fireEvent.change(input, { target: { value: 'Unsaved private draft' } });
      input.focus();
      fireEvent.click(
        screen.getByRole('button', {
          name: assistance[locale]['help.context'],
        }),
      );
      expect(screen.getByRole('dialog')).toHaveAttribute(
        'dir',
        locale === 'ar' ? 'rtl' : 'ltr',
      );
      expect(
        screen.getByText(assistance[locale]['help.remoteOff']),
      ).toBeVisible();
      fireEvent.click(
        screen.getByRole('button', { name: assistance[locale]['help.close'] }),
      );
      await waitFor(() =>
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
      );
      expect(input).toHaveValue('Unsaved private draft');
      expect(submit).not.toHaveBeenCalled();
    },
  );
  it(
    'describes a save button by its operation, never as an optional field ' +
      locale,
    async () => {
      await i18n.changeLanguage(locale);
      const submit = vi.fn();
      render(<Form submit={submit} disabled />);
      fireEvent.click(
        screen.getByRole('button', {
          name: assistance[locale]['element.explainNamed'].replace(
            '{{name}}',
            i18n.t('d1.save'),
          ),
        }),
      );
      const box = screen.getByTestId('element-explanation');
      expect(box).toHaveTextContent(assistance[locale]['element.kind_button']);
      expect(box).toHaveTextContent(
        assistance[locale]['element.rule.reference'],
      );
      expect(box).toHaveTextContent(assistance[locale]['element.disabled']);
      expect(box).not.toHaveTextContent(assistance[locale]['help.optional']);
      expect(box).not.toHaveTextContent(assistance[locale]['help.required']);
      expect(submit).not.toHaveBeenCalled();
    },
  );
  it(
    'marks conversational and voice integration pending without activating controls ' +
      locale,
    async () => {
      await i18n.changeLanguage(locale);
      render(<Form submit={vi.fn()} />);
      fireEvent.click(
        screen.getByRole('button', {
          name: assistance[locale]['help.assistant'],
        }),
      );
      expect(screen.getByTestId('assistant-conversation')).toHaveTextContent(
        assistanceV2[locale]['assist.unavailable']!,
      );
      const question = screen.getByRole('textbox', {
        name: assistanceV2[locale]['assist.question']!,
      });
      fireEvent.change(question, {
        target: { value: 'Why is this unavailable?' },
      });
      fireEvent.click(
        screen.getByRole('button', {
          name: assistanceV2[locale]['assist.send']!,
        }),
      );
      expect(screen.getByText('Why is this unavailable?')).toBeVisible();
      expect(
        screen.getByRole('button', {
          name: assistance[locale]['voice.listen'],
        }),
      ).toBeDisabled();
      expect(
        screen.getByRole('button', { name: assistance[locale]['voice.mic'] }),
      ).toBeDisabled();
      fireEvent.change(question, { target: { value: 'Retained question' } });
      fireEvent.click(
        screen.getByRole('button', { name: assistance[locale]['help.close'] }),
      );
      fireEvent.click(
        screen.getByRole('button', {
          name: assistance[locale]['help.assistant'],
        }),
      );
      expect(screen.getByRole('textbox')).toHaveValue('Retained question');
      expect(screen.getByText('Why is this unavailable?')).toBeVisible();
    },
  );
}
it('does not treat previous focus as an explicit selection', async () => {
  await i18n.changeLanguage('fr');
  render(<Form submit={vi.fn()} />);
  screen.getByLabelText('Draft').focus();
  fireEvent.click(
    screen.getByRole('button', { name: assistance.fr['help.open'] }),
  );
  fireEvent.click(
    screen.getByRole('button', { name: assistance.fr['help.fieldHelp'] }),
  );
  expect(screen.getByTestId('element-explanation')).toHaveTextContent(
    assistance.fr['help.noField'],
  );
});
it('explains explicit fields and lists without reading or modifying their values', async () => {
  await i18n.changeLanguage('fr');
  const submit = vi.fn();
  render(<Form submit={submit} />);
  const input = screen.getByLabelText('Draft');
  fireEvent.change(input, { target: { value: 'SECRET-NOT-CONTEXT' } });
  fireEvent.click(
    screen.getByRole('button', {
      name: assistance.fr['element.explainNamed'].replace(
        '{{name}}',
        d1Fr['d1.code'],
      ),
    }),
  );
  let box = screen.getByTestId('element-explanation');
  expect(box).toHaveTextContent(assistance.fr['element.rule.code']);
  expect(box).toHaveTextContent(assistance.fr['help.required']);
  expect(box).not.toHaveTextContent('SECRET-NOT-CONTEXT');
  fireEvent.click(
    screen.getByRole('button', { name: assistance.fr['help.close'] }),
  );
  fireEvent.click(
    screen.getByRole('button', {
      name: assistance.fr['element.explainNamed'].replace(
        '{{name}}',
        d1Fr['d1.referenceKind'],
      ),
    }),
  );
  box = screen.getByTestId('element-explanation');
  expect(box).toHaveTextContent(assistance.fr['element.kind_select']);
  expect(box).toHaveTextContent(assistance.fr['element.rule.referenceKind']);
  expect(input).toHaveValue('SECRET-NOT-CONTEXT');
  expect(submit).not.toHaveBeenCalled();
});
it('refuses an unsupported explanation instead of guessing', async () => {
  await i18n.changeLanguage('fr');
  render(<Form submit={vi.fn()} unknown />);
  fireEvent.click(
    screen.getByRole('button', {
      name: assistance.fr['element.explainNamed'].replace(
        '{{name}}',
        d1Fr['d1.description'],
      ),
    }),
  );
  expect(screen.getByTestId('element-explanation')).toHaveTextContent(
    assistance.fr['element.unavailable'],
  );
  expect(screen.getByTestId('element-explanation')).not.toHaveTextContent(
    assistance.fr['help.optional'],
  );
});
it('guides focus without editing or submitting', async () => {
  await i18n.changeLanguage('fr');
  const submit = vi.fn();
  render(<Form submit={submit} />);
  fireEvent.click(
    screen.getByRole('button', { name: assistance.fr['help.context'] }),
  );
  fireEvent.click(
    screen.getByRole('button', { name: assistance.fr['help.next'] }),
  );
  await waitFor(() =>
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
  );
  expect(screen.getByLabelText('Draft')).toHaveFocus();
  expect(screen.getByLabelText('Draft')).toHaveValue('');
  expect(submit).not.toHaveBeenCalled();
});
it('validates selection metadata, fixed fields and unavailable elements', () => {
  const area = document.createElement('form');
  area.dataset.operation = 'reference';
  area.innerHTML =
    '<input id="code-fixed" data-help-label="code" data-help-disabled="fixedReference" disabled><input id="secret" type="password" data-help-label="code"><div id="unknown" data-help-label="not-a-key"></div><fieldset id="busy" data-help-busy="true" disabled><button id="busy-save" data-help-label="save">Save</button></fieldset>';
  document.body.append(area);
  try {
    expect(readSelectedElement('code-fixed')?.disabledReason).toBe(
      'fixedReference',
    );
    expect(readSelectedElement('busy-save')?.disabledReason).toBe('busy');
    expect(
      elementRule({ ...readSelectedElement('code-fixed')!, kind: 'other' }),
    ).toBeNull();
    expect(readSelectedElement('secret')).toBeNull();
    expect(readSelectedElement('unknown')).toBeNull();
    expect(readSelectedElement('absent')).toBeNull();
    expect(
      elementRule({
        ...readSelectedElement('code-fixed')!,
        labelKey: 'description',
      }),
    ).toBeNull();
  } finally {
    area.remove();
  }
});
