// MoulAI™ — navigation flags only; no values are persisted or business actions replayed.
import { useState } from 'react';
import { Link, Outlet, RouterProvider, createMemoryRouter } from 'react-router';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import i18n from '../../src/shared/i18n';
import {
  UnsavedChangesProvider,
  useUnsavedChanges,
  useViewChange,
} from '../../src/shared/ui/UnsavedChanges';

function Editor() {
  const [value, setValue] = useState(''),
    [saved, setSaved] = useState(false),
    [view, setView] = useState(false);
  useUnsavedChanges(Boolean(value) && !saved);
  const change = useViewChange();
  return (
    <>
      <label>
        Name
        <input
          value={value}
          onChange={(event) => {
            setSaved(false);
            setValue(event.target.value);
          }}
        />
      </label>
      <button onClick={() => setSaved(true)}>Confirmed save</button>
      <button onClick={() => change(() => setView(true))}>Other branch</button>
      {view && <p>Changed branch</p>}
      <Link to="/next">Next</Link>
    </>
  );
}
async function start() {
  await i18n.changeLanguage('fr');
  const router = createMemoryRouter([
    {
      element: (
        <UnsavedChangesProvider>
          <Outlet />
        </UnsavedChangesProvider>
      ),
      children: [
        { path: '/', element: <Editor /> },
        { path: '/next', element: <p>Next view</p> },
        { path: '/access', element: <p>Expired session</p> },
      ],
    },
  ]);
  render(<RouterProvider router={router} />);
  return { router, user: userEvent.setup() };
}
describe('explicit unsaved navigation decisions', () => {
  it('cancels a route change without losing entered text, then discards explicitly', async () => {
    const { user } = await start();
    await user.type(screen.getByLabelText('Name'), 'Kept draft');
    await user.click(screen.getByRole('link', { name: 'Next' }));
    expect(screen.getByRole('dialog')).toHaveTextContent(
      i18n.t('quality.unsavedBody'),
    );
    await user.click(
      screen.getByRole('button', { name: i18n.t('quality.stay') }),
    );
    expect(screen.getByLabelText('Name')).toHaveValue('Kept draft');
    await user.click(screen.getByRole('link', { name: 'Next' }));
    await user.click(
      screen.getByRole('button', { name: i18n.t('quality.leave') }),
    );
    expect(await screen.findByText('Next view')).toBeVisible();
  });
  it('protects an in-place branch change and Escape preserves the input', async () => {
    const { user } = await start();
    await user.type(screen.getByLabelText('Name'), 'Unsaved');
    await user.click(screen.getByRole('button', { name: 'Other branch' }));
    expect(screen.queryByText('Changed branch')).toBeNull();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(screen.getByLabelText('Name')).toHaveValue('Unsaved');
  });
  it('does not warn after a confirmed save', async () => {
    const { user } = await start();
    await user.type(screen.getByLabelText('Name'), 'Saved');
    await user.click(screen.getByRole('button', { name: 'Confirmed save' }));
    await user.click(screen.getByRole('link', { name: 'Next' }));
    expect(await screen.findByText('Next view')).toBeVisible();
    expect(screen.queryByRole('dialog')).toBeNull();
  });
  it('does not clear another still-mounted form when confirming an in-place view change', async () => {
    const { user } = await start();
    await user.type(screen.getByLabelText('Name'), 'Still unsaved');
    await user.click(screen.getByRole('button', { name: 'Other branch' }));
    await user.click(
      screen.getByRole('button', { name: i18n.t('quality.leave') }),
    );
    expect(screen.getByText('Changed branch')).toBeVisible();
    await user.click(screen.getByRole('link', { name: 'Next' }));
    expect(screen.getByRole('dialog')).toBeVisible();
    await user.keyboard('{Escape}');
    expect(screen.getByLabelText('Name')).toHaveValue('Still unsaved');
  });
  it('never blocks a session-expiry return to sign-in', async () => {
    const { user, router } = await start();
    await user.type(screen.getByLabelText('Name'), 'Unsaved');
    await user.click(screen.getByRole('link', { name: 'Next' }));
    expect(screen.getByRole('dialog')).toBeVisible();
    act(() => window.dispatchEvent(new Event('moulai-session-expired')));
    await act(async () => {
      await router.navigate('/access');
    });
    expect(await screen.findByText('Expired session')).toBeVisible();
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});
