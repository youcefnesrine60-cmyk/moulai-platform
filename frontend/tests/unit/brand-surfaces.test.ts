// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { inflateSync } from 'node:zlib';
import { describe, expect, it } from 'vitest';
import manifest from '../../brand-sources/logo-manifest.json' with { type: 'json' };

/** Compute WCAG luminance after compositing the real panel token over scenery. */
function luminance(rgb: readonly number[]): number {
  const linear = rgb.map((channel) => {
    const value = channel / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return linear[0]! * 0.2126 + linear[1]! * 0.7152 + linear[2]! * 0.0722;
}

/** Resolve approved opaque anchors independently of the translucent panel mix. */
function rgb(tokens: Record<string, string>, name: string): number[] {
  const value = tokens[name];
  if (!value) throw new Error(`Missing token ${name}`);
  const alias = /^var\((--[\w-]+)\)$/.exec(value);
  if (alias?.[1]) return rgb(tokens, alias[1]);
  if (!/^#[a-f0-9]{6}$/i.test(value))
    throw new Error(`Non-opaque anchor ${name}`);
  return [1, 3, 5].map((offset) =>
    parseInt(value.slice(offset, offset + 2), 16),
  );
}

const css = readFileSync('src/shared/styles/tokens.css', 'utf8');
/** Extract the actual declarations; tests do not substitute an independent palette. */
function declarations(block: string): Record<string, string> {
  return Object.fromEntries(
    [...block.matchAll(/(--[\w-]+):\s*([^;]+);/g)].map((match) => [
      match[1]!,
      match[2]!.trim(),
    ]),
  );
}
const light = declarations(css.match(/:root\s*\{([\s\S]*?)\}/)?.[1] ?? '');
const dark = {
  ...light,
  ...declarations(
    css.match(/:root\[data-theme='dark'\]\s*\{([\s\S]*?)\}/)?.[1] ?? '',
  ),
};

describe('readable-panel contrast bounds over the shared scene wash', () => {
  for (const [theme, tokens] of [
    ['light', light],
    ['dark', dark],
  ] as const)
    it.each([
      ['--text-primary', 4.5],
      ['--text-secondary', 4.5],
      ['--text-muted', 4.5],
      ['--accent', 4.5],
      ['--focus', 3],
      ['--border-strong', 3],
    ] as const)(
      `${theme}: %s is readable at every RGB backdrop extreme`,
      (foreground, minimum) => {
        const alpha = parseFloat(tokens['--reading-opacity']!) / 100;
        expect(alpha).toBeGreaterThan(0.75);
        expect(alpha).toBeLessThan(1);
        expect(tokens['--surface-reading']).toContain('var(--reading-opacity)');
        expect(parseFloat(tokens['--panel-opacity']!)).toBe(60);
        expect(tokens['--surface-panel']).toContain('var(--panel-opacity)');
        expect(tokens['--surface-scene-wash']).toContain('16%');
        const base = rgb(tokens, '--surface-card');
        const page = rgb(tokens, '--surface-page');
        const text = luminance(rgb(tokens, foreground));
        for (const red of [0, 255])
          for (const green of [0, 255])
            for (const blue of [0, 255]) {
              const behind = [red, green, blue];
              const composite = luminance(
                base.map(
                  (channel, index) =>
                    channel * alpha +
                    (page[index]! * 0.16 + behind[index]! * 0.84) * (1 - alpha),
                ),
              );
              expect(
                (Math.max(text, composite) + 0.05) /
                  (Math.min(text, composite) + 0.05),
              ).toBeGreaterThanOrEqual(minimum);
            }
      },
    );
});

describe('unframed signature contrast over the existing translucent header', () => {
  for (const [theme, tokens] of [
    ['light', light],
    ['dark', dark],
  ] as const)
    it(`${theme}: primary signature text remains readable without a capsule`, () => {
      expect(tokens['--surface-header']).toContain('60%');
      expect(tokens['--surface-scene-wash']).toContain('16%');
      const page = rgb(tokens, '--surface-page');
      const text = luminance(rgb(tokens, '--text-primary'));
      for (const red of [0, 255])
        for (const green of [0, 255])
          for (const blue of [0, 255]) {
            const behind = [red, green, blue];
            const background = luminance(
              page.map(
                (channel, index) =>
                  channel * 0.6 +
                  (channel * 0.16 + behind[index]! * 0.84) * 0.4,
              ),
            );
            expect(
              (Math.max(text, background) + 0.05) /
                (Math.min(text, background) + 0.05),
            ).toBeGreaterThanOrEqual(4.5);
          }
    });
});

describe('local Light editorial surface retains readable copy and large heading contrast', () => {
  const styles = readFileSync('src/features/access/access.module.css', 'utf8');
  const surface = declarations(
    styles.match(/\.servicePresentation\s*\{([\s\S]*?)\}/)?.[1] ?? '',
  );
  const alpha = parseFloat(surface['--service-surface-opacity']!) / 100;
  it.each([
    ['--text-primary', 4.5],
    ['--text-secondary', 4.5],
    ['--text-muted', 4.5],
    ['--accent', 3],
  ] as const)(
    '%s remains readable with the actual local opacity',
    (foreground, minimum) => {
      expect(alpha).toBe(0.8);
      // Accent is reserved for the >=20px bold heading and decorative 28px icons.
      expect(styles).toContain('font-weight: var(--weight-bold)');
      const page = rgb(light, '--surface-page');
      const base = rgb(light, '--surface-card');
      const text = luminance(rgb(light, foreground));
      for (const red of [0, 255])
        for (const green of [0, 255])
          for (const blue of [0, 255]) {
            const behind = [red, green, blue];
            const background = luminance(
              base.map(
                (channel, index) =>
                  channel * alpha +
                  (page[index]! * 0.16 + behind[index]! * 0.84) * (1 - alpha),
              ),
            );
            expect(
              (Math.max(text, background) + 0.05) /
                (Math.min(text, background) + 0.05),
            ).toBeGreaterThanOrEqual(minimum);
          }
    },
  );
});

describe('byte-identical transparent official logos', () => {
  it.each(manifest.sources)(
    'preserves the $theme PNG and its transparent top-left pixel',
    (source) => {
      const bytes = readFileSync(`public/brand/${source.file}`);
      expect(createHash('sha256').update(bytes).digest('hex')).toBe(
        source.sha256,
      );
      expect(bytes.readUInt32BE(16)).toBe(source.width);
      expect(bytes.readUInt32BE(20)).toBe(source.height);
      expect(bytes[24]).toBe(8);
      expect(bytes[25]).toBe(6);
      const chunks: Buffer[] = [];
      for (let offset = 8; offset < bytes.length;) {
        const length = bytes.readUInt32BE(offset);
        if (bytes.subarray(offset + 4, offset + 8).toString() === 'IDAT')
          chunks.push(bytes.subarray(offset + 8, offset + 8 + length));
        offset += length + 12;
      }
      // At the first RGBA pixel, all PNG predictor neighbors are zero.
      expect(inflateSync(Buffer.concat(chunks))[4]).toBe(0);
    },
  );
});
