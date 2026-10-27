// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { intelligenceFr } from './intelligence.fr';

export const intelligenceEn: Record<keyof typeof intelligenceFr, string> = {
  'intelligence.boundary':
    'Local review: synthetic agents, channels and exchanges. No connected provider. This module’s data is cleared when leaving the scope.',
  'intelligence.agentIntro':
    'View the selected restaurant’s agents and their descriptive settings.',
  'intelligence.channelIntro':
    'Channels belonging to this restaurant’s agents. Indicators describe review records, not a real connection.',
  'intelligence.conversationIntro':
    'Read exchanges within the selected scope. This view is not real-time.',
  'intelligence.name': 'Name',
  'intelligence.description': 'Description',
  'intelligence.language': 'Agent language',
  'intelligence.tone': 'Tone',
  'intelligence.tone.professional': 'Professional',
  'intelligence.tone.casual': 'Casual',
  'intelligence.tone.friendly': 'Friendly',
  'intelligence.status': 'Status',
  'intelligence.all': 'All',
  'intelligence.search': 'Search',
  'intelligence.agent': 'Agent',
  'intelligence.channelType': 'Channel type',
  'intelligence.channel.telegram': 'Telegram',
  'intelligence.channel.whatsapp': 'WhatsApp',
  'intelligence.channel.web': 'Web',
  'intelligence.channel.messenger': 'Messenger',
  'intelligence.channel.api': 'API',
  'intelligence.status.active': 'Active',
  'intelligence.status.closed': 'Closed',
  'intelligence.status.suspended': 'Suspended',
  'intelligence.openAgent': 'View agent',
  'intelligence.openChannel': 'View channel',
  'intelligence.openConversation': 'View conversation',
  'intelligence.created': 'Created',
  'intelligence.updated': 'Last updated',
  'intelligence.notProvided': 'Not provided',
  'intelligence.configure': 'Configure in local review',
  'intelligence.closeEditor': 'Close the form',
  'intelligence.safeConfig':
    'Advanced JSON settings and AI parameters lack a safe public contract. Integration is deferred; no activation is available here.',
  'intelligence.channelBoundary':
    'Provider configuration, credentials, tokens and webhooks are not exposed. Channel connections and operations await Business Integration.',
  'intelligence.editNotice':
    'Synthetic descriptive changes only. No remote save or real activation.',
  'intelligence.confirmTitle': 'Review the local change',
  'intelligence.backEdit': 'Back to form',
  'intelligence.applyReview': 'Apply to local review',
  'intelligence.preview': 'Review change',
  'intelligence.invalid': 'Check this field and its limits.',
  'intelligence.stale':
    'The review changed. Close the form and reload the information.',
  'intelligence.failed':
    'Change not applied. Check your scope before trying again.',
  'intelligence.pagination': 'Pagination',
  'intelligence.previous': 'Previous',
  'intelligence.next': 'Next',
  'intelligence.pageCount': 'Page {{page}} / {{pages}} · {{count}} items',
  'intelligence.visitor': 'Unnamed visitor',
  'intelligence.participant': 'Participant identifier',
  'intelligence.messages': 'Messages',
  'intelligence.emptyMessages': 'This conversation has no messages.',
  'intelligence.role.user': 'Customer',
  'intelligence.role.assistant': 'Assistant',
  'intelligence.role.system': 'System',
  'intelligence.mediaBoundary': 'Media content displayed as text only',
  'intelligence.media.image': 'Image',
  'intelligence.media.audio': 'Audio',
  'intelligence.media.video': 'Video',
  'intelligence.media.file': 'File',
  'intelligence.readOnly':
    'Read only. Sending, real-time updates and status transitions await Business Integration.',
};
