// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Reuse the exercised integrated dining recipe; preserve previous evidence.
process.argv.push('--staging-followup');
await import('./check-operational-dining-o4.mjs');
