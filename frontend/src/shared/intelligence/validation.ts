// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { z } from 'zod';
import { agentTones, conversationStatuses } from './contracts';

/** AgentUpdate's documented fields only; activation and arbitrary JSON are not accepted. */
export const agentDraftSchema = z
  .object({
    name: z.string().max(100).trim().min(1),
    description: z.string().max(500),
    language: z.enum(['fr', 'en', 'ar']),
    tone: z.enum(agentTones),
  })
  .strict();
export const conversationFilterSchema = z
  .object({
    query: z.string().max(100),
    agentId: z.number().int().positive().safe().nullable(),
    status: z.enum(['all', ...conversationStatuses]),
    skip: z.number().int().nonnegative().safe(),
  })
  .strict();
export const pageSize = 5;
