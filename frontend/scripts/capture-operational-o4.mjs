// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Read-only captures of the actual paid recipe. Voice metadata never requests the microphone or plays audio.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {
  launch,
  login,
  root,
  request,
  checked,
} from './operationalHarness.mjs';
const output = path.join(root, 'artifacts/operational-o3-20261108');
assert.equal(
  JSON.parse(
    fs.readFileSync(path.join(output, 'saas-review-resume.json'), 'utf8'),
  ).status,
  'PASS',
);
const browser = await launch(),
  captures = [];
try {
  const owner = await login(browser, 'billing-scenario');
  await owner.goto(
    'https://127.0.0.1:5180/workspace/organizations/11/restaurants/9/offer',
  );
  for (const locale of ['fr', 'en', 'ar']) {
    await owner.evaluate(
      (locale) => localStorage.setItem('moulai.locale', locale),
      locale,
    );
    await owner.reload();
    await owner
      .getByRole('heading', {
        name: { fr: 'Mon offre SaaS', en: 'My SaaS offer', ar: 'عرض اشتراكي' }[
          locale
        ],
        exact: true,
      })
      .waitFor();
    const payments = checked(
      await request(
        owner,
        '/api/web/organizations/11/restaurants/9/saas-payments',
      ),
    );
    assert.equal(payments.length, 1);
    assert.equal(payments[0].status, 'paid');
    for (const theme of ['light', 'dark'])
      for (const [viewport, size] of Object.entries({
        desktop: { width: 1440, height: 1000 },
        mobile: { width: 390, height: 844 },
      })) {
        await owner.setViewportSize(size);
        await owner.evaluate(
          (theme) => window.moulaiTheme.choose(theme),
          theme,
        );
        await owner.evaluate(() => document.fonts.ready);
        const facts = await owner.evaluate(() => ({
          dir: document.documentElement.dir,
          overflow: document.documentElement.scrollWidth > innerWidth,
          keys:
            document.body.innerText.match(
              /\b(?:o3|integration|offer)\.[A-Za-z_]+/g,
            ) || [],
        }));
        assert.equal(facts.dir, locale === 'ar' ? 'rtl' : 'ltr');
        assert.equal(facts.overflow, false);
        assert.deepEqual(facts.keys, []);
        const file = `paid-offer-${locale}-${theme}-${viewport}.png`;
        await owner.screenshot({
          path: path.join(output, file),
          fullPage: true,
          animations: 'disabled',
        });
        captures.push({ file, locale, theme, viewport, ...facts });
      }
  }
  const voice = await owner.evaluate(() => ({
    speechSynthesisAvailable: typeof speechSynthesis !== 'undefined',
    localVoiceLanguages:
      typeof speechSynthesis === 'undefined'
        ? []
        : [
            ...new Set(
              speechSynthesis
                .getVoices()
                .filter((v) => v.localService === true)
                .map((v) => v.lang),
            ),
          ],
    recognitionApi:
      typeof window.SpeechRecognition === 'function' ||
      typeof window.webkitSpeechRecognition === 'function',
    microphoneRequested: false,
    audioPlayed: false,
  }));
  const admin = await login(browser, 'platform-admin');
  await admin
    .getByRole('link', { name: 'Offres SaaS — campagnes', exact: true })
    .click();
  const contexts = checked(
    await request(admin, '/api/web/platform/pricing/base-contexts'),
  );
  assert.deepEqual(contexts, [{ country_code: 'DZ', currency: 'DZD' }]);
  await admin
    .getByRole('heading', { name: /Base SaaS|Prix de base/ })
    .first()
    .waitFor();
  await admin.screenshot({
    path: path.join(output, 'country-base-editor-fr.png'),
    fullPage: true,
  });
  fs.writeFileSync(
    path.join(output, 'captures-final.json'),
    JSON.stringify(
      {
        status: 'PASS',
        captures,
        voice,
        pricingContexts: contexts,
        mutations: false,
        externalCalls: false,
      },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({
      status: 'PASS',
      captures: captures.length,
      pricingContexts: contexts,
    }),
  );
} catch (error) {
  fs.writeFileSync(
    path.join(output, 'captures-final.json'),
    JSON.stringify(
      { status: 'FAIL', type: error.constructor.name, captures },
      null,
      2,
    ),
  );
  console.error(
    JSON.stringify({
      status: 'FAIL',
      type: error.constructor.name,
      captures: captures.length,
    }),
  );
  process.exitCode = 1;
} finally {
  await browser.close();
}
