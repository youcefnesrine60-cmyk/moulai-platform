// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { RestaurantScope } from '../business/contracts';
import type { Locale } from '../access/contracts';

export const agentTones = ['professional', 'casual', 'friendly'] as const;
export const channelTypes = [
  'telegram',
  'whatsapp',
  'web',
  'messenger',
  'api',
] as const;
export const conversationStatuses = ['active', 'closed', 'suspended'] as const;
export type AgentTone = (typeof agentTones)[number];
export type ChannelType = (typeof channelTypes)[number];
export type ConversationStatus = (typeof conversationStatuses)[number];

/** Explicit safe projections of app/schemas/agent; raw config/AI/context JSON is excluded. */
export interface AgentView {
  readonly id: number;
  readonly restaurantId: number;
  readonly name: string;
  readonly description: string;
  readonly language: Locale;
  readonly tone: AgentTone;
  readonly active: boolean;
  readonly createdAt: string;
  readonly updatedAt: string;
}
export interface ChannelView {
  readonly id: number;
  readonly agentId: number;
  readonly name: string;
  readonly type: ChannelType;
  readonly active: boolean;
  readonly createdAt: string;
  readonly updatedAt: string;
}
export interface ConversationView {
  readonly id: number;
  readonly agentId: number;
  readonly channelId: number;
  readonly userId: string;
  readonly userName: string | null;
  readonly status: ConversationStatus;
  readonly active: boolean;
  readonly createdAt: string;
  readonly updatedAt: string;
}
export interface MessageView {
  readonly id: number;
  readonly conversationId: number;
  readonly role: 'user' | 'assistant' | 'system';
  readonly content: string;
  readonly contentType: 'text' | 'image' | 'audio' | 'video' | 'file';
  readonly createdAt: string;
  readonly updatedAt: string;
}
export interface AgentWorkspace {
  /** Ephemeral optimistic review revision, not an existing HTTP field. */
  readonly reviewRevision: number;
  readonly agents: readonly AgentView[];
  readonly channels: readonly ChannelView[];
}
export interface PageResult<T> {
  readonly items: readonly T[];
  readonly total: number;
  readonly skip: number;
  readonly limit: number;
}
export interface ConversationFilter {
  readonly query: string;
  readonly agentId: number | null;
  readonly status: ConversationStatus | 'all';
  readonly skip: number;
}
export interface AgentDraft {
  readonly name: string;
  readonly description: string;
  readonly language: Locale;
  readonly tone: AgentTone;
}

/** View-adapter operations, not invented endpoints; all current effects stay in memory. */
export interface IntelligenceAdapter {
  agentWorkspace(
    scope: RestaurantScope,
    signal: AbortSignal,
  ): Promise<AgentWorkspace>;
  conversations(
    scope: RestaurantScope,
    filter: ConversationFilter,
    signal: AbortSignal,
  ): Promise<PageResult<ConversationView>>;
  conversation(
    scope: RestaurantScope,
    id: number,
    signal: AbortSignal,
  ): Promise<ConversationView>;
  messages(
    scope: RestaurantScope,
    conversationId: number,
    skip: number,
    signal: AbortSignal,
  ): Promise<PageResult<MessageView>>;
  saveAgentReview(
    scope: RestaurantScope,
    id: number,
    revision: number,
    draft: AgentDraft,
    signal: AbortSignal,
  ): Promise<void>;
  /** Drop transient module data on scope exit; never a remote deletion. */
  releaseAgentScope(scope: RestaurantScope): void;
}
