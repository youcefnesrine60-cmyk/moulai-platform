// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Select the dated followup scope without duplicating the existing recipe.
process.argv.push('--staging-followup');
await import('./check-operational-autonomous.mjs');
