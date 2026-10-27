// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { ReactElement, ReactNode } from 'react';
import { useTheme } from '../theme';
import styles from './brand-canvas.module.css';

/** Share decorative approved artwork without remounting routes, forms or providers. */
export function BrandCanvas({
  children,
}: {
  children: ReactNode;
}): ReactElement {
  const { theme } = useTheme();
  return (
    <div className={styles.canvas}>
      <div
        className={styles.background}
        data-gateway={theme}
        aria-hidden="true"
      >
        <img
          key={theme}
          src={`/brand/gateway/${theme}-1672.webp`}
          srcSet={[640, 1024, 1672]
            .map((width) => `/brand/gateway/${theme}-${width}.webp ${width}w`)
            .join(', ')}
          sizes="100vw"
          width={1672}
          height={941}
          alt=""
          decoding="async"
          fetchPriority="high"
        />
      </div>
      {children}
    </div>
  );
}
