// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type {
  AgentWorkspace,
  ConversationView,
  MessageView,
} from '../shared/intelligence/contracts';

/** Merchant-authored names/messages remain verbatim when interface language changes. */
export function intelligenceFixture(restaurantId: number): {
  workspace: AgentWorkspace;
  conversations: ConversationView[];
  messages: MessageView[];
} {
  const base = restaurantId * 100;
  const at = (minute: number): string =>
    new Date(Date.UTC(2026, 9, 20, 10, minute)).toISOString();
  if (restaurantId === 9202)
    return {
      workspace: { reviewRevision: 1, agents: [], channels: [] },
      conversations: [],
      messages: [],
    };
  const agents: AgentWorkspace['agents'] = [
    {
      id: base + 1,
      restaurantId,
      name: `Accueil · IA-REV-${restaurantId}`,
      description: 'Agent de revue synthétique — مساعد المراجعة',
      language: 'fr',
      tone: 'professional',
      active: true,
      createdAt: at(0),
      updatedAt: at(1),
    },
    {
      id: base + 2,
      restaurantId,
      name: `Service · IA-REV-${restaurantId}`,
      description: '',
      language: 'ar',
      tone: 'friendly',
      active: false,
      createdAt: at(0),
      updatedAt: at(2),
    },
  ];
  const channels: AgentWorkspace['channels'] = [
    {
      id: base + 11,
      agentId: base + 1,
      name: `Canal web de revue ${restaurantId}`,
      type: 'web',
      active: true,
      createdAt: at(0),
      updatedAt: at(1),
    },
    {
      id: base + 12,
      agentId: base + 1,
      name: `Canal Telegram de revue ${restaurantId}`,
      type: 'telegram',
      active: false,
      createdAt: at(0),
      updatedAt: at(1),
    },
    {
      id: base + 13,
      agentId: base + 2,
      name: `Canal API de revue ${restaurantId}`,
      type: 'api',
      active: false,
      createdAt: at(0),
      updatedAt: at(1),
    },
  ];
  const conversations: ConversationView[] = Array.from(
    { length: 7 },
    (_, index) => ({
      id: base + 21 + index,
      agentId: base + 1,
      channelId: base + 11,
      userId: `synthetic-visitor-${restaurantId}-${index + 1}`,
      userName: index === 6 ? null : `Visiteur de revue ${index + 1}`,
      status: index === 2 ? 'suspended' : index === 1 ? 'closed' : 'active',
      active: index !== 1 && index !== 2,
      createdAt: at(index),
      updatedAt: at(index + 12),
    }),
  );
  const messages: MessageView[] = Array.from({ length: 12 }, (_, index) => ({
    id: base + 101 + index,
    conversationId: base + 21,
    role: index === 0 ? 'system' : index % 2 === 0 ? 'assistant' : 'user',
    contentType: index === 9 ? 'image' : 'text',
    content:
      index === 0
        ? 'Conversation synthétique de revue. Aucun service réel.'
        : index === 3
          ? 'رسالة تجريبية طويلة\nنرغب في الاستفسار عن الخيارات المتاحة. '.repeat(
              14,
            )
          : index === 9
            ? 'Pièce jointe synthétique — aperçu multimédia non connecté.'
            : index === 4
              ? '<script>contenu de test affiché comme texte</script>\nNo HTML execution.'
              : `Échange synthétique ${index + 1} — مرحبًا — Local review only.`,
    createdAt: at(index),
    updatedAt: at(index),
  }));
  return {
    workspace: { reviewRevision: 1, agents, channels },
    conversations,
    messages,
  };
}
