// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Select approved originals for the actual surface; print media always uses the light artwork on white paper.
import type { ReactElement } from 'react';
import { useTheme } from '../theme';
import { brandArtwork } from './brandArtwork';

/** A single accessible image switches source before print layout, without filters or asset mutation. */
export function BrandLogo({
  className,
  surface = 'theme',
  priority = false,
}: {
  className?: string | undefined;
  surface?: 'theme' | 'light' | 'dark';
  priority?: boolean;
}): ReactElement {
  const { theme } = useTheme();
  const artwork = brandArtwork[surface === 'theme' ? theme : surface];
  return (
    <picture data-approved-brand-logo>
      <source
        media="print"
        srcSet={brandArtwork.light.src}
        width={brandArtwork.light.width}
        height={brandArtwork.light.height}
      />
      <img
        className={className}
        src={artwork.src}
        alt="MoulAI™"
        width={artwork.width}
        height={artwork.height}
        decoding="async"
        fetchPriority={priority ? 'high' : 'auto'}
      />
    </picture>
  );
}
