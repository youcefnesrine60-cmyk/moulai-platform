// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { render, screen, type RenderResult } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { beforeEach, describe, expect, it } from 'vitest';
import { Providers, createQueryClient } from '../../src/app/Providers';
import { routes } from '../../src/app/router';
import { disconnectedAdapter } from '../../src/shared/access/disconnected';
import { Brand } from '../../src/shared/ui/primitives';
import i18n from '../../src/shared/i18n';
import manifest from '../../brand-sources/gateway/manifest.json' with { type: 'json' };

/** Mount the actual disconnected route; decorative artwork cannot enable access. */
async function access(): Promise<RenderResult> {
  const result = render(
    <Providers adapter={disconnectedAdapter} client={createQueryClient()}>
      <RouterProvider
        router={createMemoryRouter(routes, { initialEntries: ['/access'] })}
      />
    </Providers>,
  );
  await screen.findByRole('heading', { name: i18n.t('access.title') });
  return result;
}

beforeEach(async () => {
  window.moulaiTheme.choose('light');
  await i18n.changeLanguage('fr');
});

describe('approved Gateway assets and access boundary', () => {
  for (const locale of ['fr', 'en', 'ar'] as const)
    for (const theme of ['light', 'dark'] as const)
      it(`${locale}/${theme} uses one decorative responsive Gateway with disconnected access`, async () => {
        await i18n.changeLanguage(locale);
        window.moulaiTheme.choose(theme);
        const { container } = await access();
        const gateway = container.querySelector(`[data-gateway="${theme}"]`);
        expect(gateway).toHaveAttribute('aria-hidden', 'true');
        expect(container.querySelectorAll('[data-gateway]')).toHaveLength(1);
        const image = gateway?.querySelector('img');
        expect(image).toHaveAttribute('alt', '');
        expect(image).toHaveAttribute(
          'src',
          `/brand/gateway/${theme}-1672.webp`,
        );
        expect(image).toHaveAttribute('sizes', '100vw');
        expect(image).toHaveAttribute('width', '1672');
        expect(image).toHaveAttribute('height', '941');
        expect(image?.getAttribute('srcset')).toContain(
          `${theme}-640.webp 640w`,
        );
        expect(image?.getAttribute('srcset')).toContain(
          `${theme}-1024.webp 1024w`,
        );
        expect(
          screen.getByRole('button', { name: i18n.t('access.signin') }),
        ).toBeDisabled();
        expect(
          screen.queryByRole('button', { name: i18n.t('review.open') }),
        ).not.toBeInTheDocument();
        expect(screen.getByAltText('MoulAI™')).toHaveAttribute(
          'src',
          `/brand/moulai-logo-${theme}01.png`,
        );
      });

  it('preserves all approved original pixels and declared optimized outputs', () => {
    for (const source of manifest.sources) {
      const bytes = readFileSync(`brand-sources/gateway/${source.original}`);
      expect(createHash('sha256').update(bytes).digest('hex')).toBe(
        source.originalSha256,
      );
      expect(bytes.readUInt32BE(16)).toBe(1672);
      expect(bytes.readUInt32BE(20)).toBe(941);
      expect(source.variants.map((variant) => variant.width)).toEqual([
        640, 1024, 1672,
      ]);
      for (const variant of source.variants) {
        const encoded = readFileSync(`public/brand/gateway/${variant.file}`);
        expect(createHash('sha256').update(encoded).digest('hex')).toBe(
          variant.sha256,
        );
        expect(encoded.length).toBe(variant.bytes);
        expect(encoded.subarray(8, 12).toString()).toBe('WEBP');
        expect(encoded.length).toBeLessThan(source.originalBytes / 8);
      }
    }
    const logo = readFileSync('public/brand/moulai-logo.png');
    expect(createHash('sha256').update(logo).digest('hex')).toBe(
      '548d877ec2d08e286aec12bc38f1969b9e8653cc18ddeaf9ff724e7cb5bb067a',
    );
  });

  it('preserves the supplied transparent artwork ratio for both brand sizes', () => {
    const { container } = render(<Brand />);
    const normal = container.firstElementChild?.className;
    const larger = render(<Brand prominent />);
    expect(larger.container.firstElementChild?.className).not.toBe(normal);
    expect(larger.container.querySelector('img')).toHaveAttribute(
      'width',
      '2172',
    );
    expect(larger.container.querySelector('img')).toHaveAttribute(
      'height',
      '724',
    );
  });
});
