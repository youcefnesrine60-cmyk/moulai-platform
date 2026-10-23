// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach } from 'vitest';
import '../../src/shared/i18n';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

// Execute the actual parser-blocking bootstrap once in each isolated test window.
runInNewContext(readFileSync('public/theme-init.js', 'utf8'), {
  window,
  document,
});

// Lazy feature imports and dependent scoped reads can exceed the one-second default.
configure({ asyncUtilTimeout: 3000 });

afterEach(() => {
  cleanup();
  localStorage.clear();
});
