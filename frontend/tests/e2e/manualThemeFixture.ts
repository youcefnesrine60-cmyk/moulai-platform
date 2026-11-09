// MoulAI™ — explicit manual appearance for historical visual fixtures, never an opening-policy mock.
import type { Page } from '@playwright/test';

/** Reproduce a tester's manual Light/Dark selection after the real bootstrap.
 * Legacy fixture storage only conveys test input. Production never reads it;
 * dining-polish.spec.ts independently checks the unmodified first paint/reopening policy.
 */
export async function installManualThemeFixture(page: Page): Promise<void> {
  await page.addInitScript(() => {
    document.addEventListener(
      'DOMContentLoaded',
      () => {
        try {
          const selected = localStorage.getItem('moulai.theme');
          if (selected === 'light' || selected === 'dark')
            window.moulaiTheme.choose(selected);
        } catch {
          // Storage-denied tests retain the actual device-local opening behavior.
        }
      },
      { once: true },
    );
  });
}
