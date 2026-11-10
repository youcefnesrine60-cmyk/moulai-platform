// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Read-only browser receipt of the shared header; real local TLS and identity.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { expect } from '@playwright/test';
import {
  launch,
  login,
  newContext,
  origin,
  root,
} from './operationalHarness.mjs';

const receiptPhase = process.argv
  .find((value) => value.startsWith('--receipt='))
  ?.split('=')[1];
assert(!receiptPhase || ['before', 'after'].includes(receiptPhase));
const output = path.join(
  root,
  receiptPhase
    ? `artifacts/interface-consolidation-20261110/${receiptPhase}`
    : 'artifacts/staging-local-followup-20261110/captures',
);
fs.mkdirSync(output, { recursive: true });
const browser = await launch();
const checks = [];
let phase = 'local-https';
try {
  const access = await (await newContext(browser)).newPage();
  const owner = await login(browser, 'owner-a');
  for (const [name, page, url] of [
    ['access', access, '/access'],
    ['workspace', owner, '/workspace/organizations/8/restaurants/6/offer'],
    [
      'tables',
      owner,
      '/workspace/organizations/8/restaurants/6/tables?branch=4',
    ],
  ]) {
    for (const locale of ['fr', 'en', 'ar']) {
      if (name !== 'access') {
        await page.goto(origin + '/api/web/auth/login');
        await page.waitForURL('**/workspace');
      }
      await page.goto(origin + '/access');
      await page.evaluate(
        (locale) => localStorage.setItem('moulai.locale', locale),
        locale,
      );
      await page.goto(origin + url);
      if (name === 'tables')
        await page.getByTestId('operational-board').waitFor();
      if (name === 'workspace')
        await page.locator('select[required]').first().waitFor();
      await page.waitForFunction(
        (locale) => document.documentElement.lang === locale,
        locale,
      );
      for (const theme of ['light', 'dark'])
        for (const [device, viewport] of Object.entries({
          desktop: { width: 1440, height: 1000 },
          mobile: { width: 390, height: 844 },
        })) {
          phase = [name, locale, theme, device].join('-');
          await page.setViewportSize(viewport);
          await page.evaluate(
            (theme) => window.moulaiTheme.choose(theme),
            theme,
          );
          await page.evaluate(() => document.fonts.ready);
          const header = page.locator('header').first();
          const dock = header.locator('[data-assistance-dock]');
          await dock.waitFor();
          await dock
            .locator('img')
            .evaluateAll((images) =>
              Promise.all(images.map((image) => image.decode())),
            );
          const facts = await header.evaluate((header) => {
            const box = (element) => {
              const r = element.getBoundingClientRect();
              return { x: r.x, y: r.y, w: r.width, h: r.height };
            };
            return {
              header: box(header),
              help: box(header.querySelector('[data-header-help]')),
              brand: box(header.querySelector('[data-header-brand]')),
              controls: box(header.querySelector('[data-header-controls]')),
              images: Array.from(
                header.querySelectorAll('[data-assistance-dock] img'),
              ).map((img) => {
                const canvas = document.createElement('canvas');
                canvas.width = img.naturalWidth;
                canvas.height = img.naturalHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                const style = getComputedStyle(img),
                  button = img.closest('button'),
                  b = getComputedStyle(button);
                return {
                  src: img.getAttribute('src'),
                  box: box(img),
                  click: box(button),
                  cornerAlpha: ctx.getImageData(0, 0, 1, 1).data[3],
                  filter: style.filter,
                  shadow: style.boxShadow,
                  background: b.backgroundColor,
                  border: b.borderWidth,
                };
              }),
              overflow: document.documentElement.scrollWidth > innerWidth + 1,
              direction: document.documentElement.dir,
            };
          });
          assert.equal(await page.title(), 'MoulAI™');
          assert.equal(facts.direction, locale === 'ar' ? 'rtl' : 'ltr');
          assert.equal(facts.overflow, false);
          assert(
            facts.help.x < facts.controls.x,
            'Physical left/right must survive RTL',
          );
          assert(facts.help.x + facts.help.w <= facts.controls.x + 1);
          assert(
            Math.abs(
              facts.brand.x +
                facts.brand.w / 2 -
                (facts.header.x + facts.header.w / 2),
            ) < 2,
          );
          for (const img of facts.images) {
            assert(img.src.endsWith('(2).png'));
            assert.equal(img.box.w, 48);
            assert.equal(img.box.h, 48);
            assert.equal(img.cornerAlpha, 0);
            assert(img.click.w >= 48 && img.click.h >= 48);
            assert.equal(img.filter, 'none');
            assert.equal(img.shadow, 'none');
            assert.equal(img.background, 'rgba(0, 0, 0, 0)');
            assert.equal(img.border, '0px');
          }
          await page.mouse.move(viewport.width - 1, viewport.height - 1);
          await page.screenshot({
            path: path.join(output, phase + '.png'),
            animations: 'disabled',
          });
          const help = dock.getByRole('button').nth(0),
            assistant = dock.getByRole('button').nth(1);
          await page.keyboard.press('Tab');
          await help.focus();
          await expect(help).toBeFocused();
          await expect(help).toHaveCSS('outline-style', 'solid');
          await help.press('Enter');
          await page.getByRole('dialog').waitFor();
          await page.keyboard.press('Escape');
          await page.getByRole('dialog').waitFor({ state: 'hidden' });
          await page.waitForFunction(
            (el) => el === document.activeElement,
            await help.elementHandle(),
          );
          await assistant.focus();
          await assistant.press('Enter');
          const dialog = page.getByRole('dialog');
          await dialog.waitFor();
          assert(await dialog.getByRole('textbox').isVisible());
          assert(
            (await dialog.innerText()).includes(
              {
                fr: 'Service IA indisponible',
                en: 'AI service unavailable',
                ar: 'خدمة الذكاء الاصطناعي غير متاحة',
              }[locale],
            ),
          );
          await page.keyboard.press('Escape');
          await dialog.waitFor({ state: 'hidden' });
          checks.push({
            phase,
            status: 'PASS',
            capture: phase + '.png',
            facts,
          });
        }
    }
  }
  fs.writeFileSync(
    path.join(output, 'results.json'),
    JSON.stringify({ status: 'PASS', tlsValidation: true, checks }, null, 2),
  );
  console.log(
    JSON.stringify({
      status: 'PASS',
      captures: checks.length,
      tlsValidation: true,
    }),
  );
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'results.json'),
    JSON.stringify(
      {
        status: 'FAIL',
        phase,
        errorType: error.constructor.name,
        message: error.message,
        checks,
      },
      null,
      2,
    ),
  );
  console.error(
    JSON.stringify({
      status: 'FAIL',
      phase,
      errorType: error.constructor.name,
      message: error.message,
    }),
  );
  process.exitCode = 1;
} finally {
  await browser.close();
}
