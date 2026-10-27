// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useEffect, useState, type ReactElement } from 'react';
import { Link, useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { useAdapter } from '../../app/access';
import { AccessError } from '../../shared/access/contracts';
import {
  channelTypes,
  conversationStatuses,
  type ConversationFilter,
} from '../../shared/intelligence/contracts';
import {
  Badge,
  Button,
  ErrorPanel,
  LoadingPanel,
} from '../../shared/ui/primitives';
import {
  EmptyResults,
  positiveId,
  useBusinessFormatting,
} from '../management/scope';
import { AgentEditor } from './AgentEditor';
import { useAgentWorkspace, useIntelligence } from './scope';
import shared from '../management/management.module.css';
import styles from './intelligence.module.css';

/** Page counters describe stored review rows, not real activity or live delivery. */
function Pager({
  skip,
  total,
  limit,
  change,
}: {
  skip: number;
  total: number;
  limit: number;
  change: (skip: number) => void;
}): ReactElement {
  const { t } = useTranslation();
  return (
    <nav className={styles.pager} aria-label={t('intelligence.pagination')}>
      <Button
        variant="secondary"
        disabled={skip === 0}
        onClick={() => change(Math.max(0, skip - limit))}
      >
        <ArrowLeft className="directional" size={16} aria-hidden="true" />
        {t('intelligence.previous')}
      </Button>
      <span aria-live="polite">
        {t('intelligence.pageCount', {
          page: Math.floor(skip / limit) + 1,
          pages: Math.max(1, Math.ceil(total / limit)),
          count: total,
        })}
      </span>
      <Button
        variant="secondary"
        disabled={skip + limit >= total}
        onClick={() => change(skip + limit)}
      >
        {t('intelligence.next')}
        <ArrowRight className="directional" size={16} aria-hidden="true" />
      </Button>
    </nav>
  );
}

/** Existing boolean status is not a claim that any provider is currently connected. */
function Active({ value }: { value: boolean }): ReactElement {
  const { t } = useTranslation();
  return <Badge>{t(value ? 'common.active' : 'common.inactive')}</Badge>;
}

/** Restaurant-bound agent search/filtering uses fields represented by AgentResponse. */
export function AgentsPage(): ReactElement {
  const { t } = useTranslation();
  const { basePath } = useIntelligence();
  const query = useAgentWorkspace();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('all');
  if (query.isPending) return <LoadingPanel />;
  if (query.isError)
    return (
      <ErrorPanel error={query.error} retry={() => void query.refetch()} />
    );
  const rows = query.data.agents.filter(
    (row) =>
      `${row.name} ${row.description}`
        .toLocaleLowerCase()
        .includes(search.trim().toLocaleLowerCase()) &&
      (status === 'all' || row.active === (status === 'active')),
  );
  return (
    <>
      <h1>{t('nav.agents')}</h1>
      <p>{t('intelligence.agentIntro')}</p>
      <div className={styles.filters}>
        <label className={shared.field}>
          {t('intelligence.search')}
          <input
            type="search"
            maxLength={100}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <label className={shared.field}>
          {t('intelligence.status')}
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="all">{t('intelligence.all')}</option>
            <option value="active">{t('common.active')}</option>
            <option value="inactive">{t('common.inactive')}</option>
          </select>
        </label>
      </div>
      {rows.length === 0 ? (
        <EmptyResults
          clear={() => {
            setSearch('');
            setStatus('all');
          }}
        />
      ) : (
        <ul className={styles.list}>
          {rows.map((row) => (
            <li className={styles.row} key={row.id}>
              <h2>
                <bdi>{row.name}</bdi>
              </h2>
              <Active value={row.active} />
              <p>
                {t('intelligence.language')}:{' '}
                <bdi>{row.language.toUpperCase()}</bdi> ·{' '}
                {t(`intelligence.tone.${row.tone}`)}
              </p>
              <p>
                {t('nav.channels')}:{' '}
                {
                  query.data.channels.filter(
                    (channel) => channel.agentId === row.id,
                  ).length
                }
              </p>
              <Link className={styles.link} to={`${basePath}/agents/${row.id}`}>
                {t('intelligence.openAgent')} · <bdi>{row.name}</bdi>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

/** Safe descriptive configuration, with an explicit permission and no arbitrary JSON editor. */
export function AgentDetailPage(): ReactElement {
  const { t } = useTranslation();
  const { agentId } = useParams();
  const { basePath, company } = useIntelligence();
  const query = useAgentWorkspace();
  const { date } = useBusinessFormatting();
  const [editing, setEditing] = useState(false);
  if (query.isPending) return <LoadingPanel />;
  if (query.isError)
    return (
      <ErrorPanel error={query.error} retry={() => void query.refetch()} />
    );
  const agent = query.data.agents.find((row) => row.id === positiveId(agentId));
  if (!agent) return <ErrorPanel error={new AccessError('notFound')} />;
  const channels = query.data.channels.filter(
    (row) => row.agentId === agent.id,
  );
  return (
    <>
      <Link className={styles.link} to={`${basePath}/agents`}>
        {t('nav.agents')}
      </Link>
      <h1 dir="auto">{agent.name}</h1>
      <Active value={agent.active} />
      <dl className={styles.facts}>
        <div>
          <dt>{t('intelligence.description')}</dt>
          <dd dir="auto">
            {agent.description || t('intelligence.notProvided')}
          </dd>
        </div>
        <div>
          <dt>{t('intelligence.language')}</dt>
          <dd>{agent.language.toUpperCase()}</dd>
        </div>
        <div>
          <dt>{t('intelligence.tone')}</dt>
          <dd>{t(`intelligence.tone.${agent.tone}`)}</dd>
        </div>
        <div>
          <dt>{t('intelligence.created')}</dt>
          <dd>
            <time dateTime={agent.createdAt}>{date(agent.createdAt)}</time>
          </dd>
        </div>
        <div>
          <dt>{t('intelligence.updated')}</dt>
          <dd>
            <time dateTime={agent.updatedAt}>{date(agent.updatedAt)}</time>
          </dd>
        </div>
      </dl>
      {company.permissions.includes('tenant.agents.manage') && (
        <Button onClick={() => setEditing(true)}>
          {t('intelligence.configure')}
        </Button>
      )}
      <p className={styles.notice}>{t('intelligence.safeConfig')}</p>
      <h2>{t('nav.channels')}</h2>
      {channels.length === 0 ? (
        <EmptyResults />
      ) : (
        <ul className={styles.list}>
          {channels.map((channel) => (
            <li key={channel.id}>
              <Link
                className={styles.link}
                to={`${basePath}/channels/${channel.id}`}
              >
                <bdi>{channel.name}</bdi>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <div className={styles.links}>
        <Link className={styles.link} to={`${basePath}/channels`}>
          {t('nav.channels')}
        </Link>
        {company.permissions.includes('tenant.conversations.read') && (
          <Link className={styles.link} to={`${basePath}/conversations`}>
            {t('nav.conversations')}
          </Link>
        )}
      </div>
      {editing && (
        <AgentEditor
          key={agent.id}
          agent={agent}
          revision={query.data.reviewRevision}
          close={() => setEditing(false)}
        />
      )}
    </>
  );
}

/** Channel browsing inherits agent-read permission; no invented channel permission or connector. */
export function ChannelsPage(): ReactElement {
  const { t } = useTranslation();
  const { basePath } = useIntelligence();
  const query = useAgentWorkspace();
  const [type, setType] = useState('all');
  const [agentId, setAgentId] = useState('all');
  const [search, setSearch] = useState('');
  if (query.isPending) return <LoadingPanel />;
  if (query.isError)
    return (
      <ErrorPanel error={query.error} retry={() => void query.refetch()} />
    );
  const rows = query.data.channels.filter(
    (row) =>
      (type === 'all' || row.type === type) &&
      (agentId === 'all' || row.agentId === Number(agentId)) &&
      row.name.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()),
  );
  return (
    <>
      <h1>{t('nav.channels')}</h1>
      <p>{t('intelligence.channelIntro')}</p>
      <div className={styles.filters}>
        <label className={shared.field}>
          {t('intelligence.search')}
          <input
            type="search"
            maxLength={100}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <label className={shared.field}>
          {t('intelligence.channelType')}
          <select
            value={type}
            onChange={(event) => setType(event.target.value)}
          >
            <option value="all">{t('intelligence.all')}</option>
            {channelTypes.map((value) => (
              <option key={value} value={value}>
                {t(`intelligence.channel.${value}`)}
              </option>
            ))}
          </select>
        </label>
        <label className={shared.field}>
          {t('intelligence.agent')}
          <select
            value={agentId}
            onChange={(event) => setAgentId(event.target.value)}
          >
            <option value="all">{t('intelligence.all')}</option>
            {query.data.agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {rows.length === 0 ? (
        <EmptyResults
          clear={() => {
            setType('all');
            setAgentId('all');
            setSearch('');
          }}
        />
      ) : (
        <ul className={styles.list}>
          {rows.map((row) => (
            <li className={styles.row} key={row.id}>
              <h2>
                <bdi>{row.name}</bdi>
              </h2>
              <Active value={row.active} />
              <p>{t(`intelligence.channel.${row.type}`)}</p>
              <p>
                {t('intelligence.agent')}:{' '}
                <bdi>
                  {
                    query.data.agents.find((agent) => agent.id === row.agentId)
                      ?.name
                  }
                </bdi>
              </p>
              <Link
                className={styles.link}
                to={`${basePath}/channels/${row.id}`}
              >
                {t('intelligence.openChannel')} · <bdi>{row.name}</bdi>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

/** Provider-neutral, non-sensitive metadata only; active is a stored flag, not health telemetry. */
export function ChannelDetailPage(): ReactElement {
  const { t } = useTranslation();
  const { channelId } = useParams();
  const { basePath, company } = useIntelligence();
  const query = useAgentWorkspace();
  const { date } = useBusinessFormatting();
  if (query.isPending) return <LoadingPanel />;
  if (query.isError)
    return (
      <ErrorPanel error={query.error} retry={() => void query.refetch()} />
    );
  const channel = query.data.channels.find(
    (row) => row.id === positiveId(channelId),
  );
  const agent = query.data.agents.find((row) => row.id === channel?.agentId);
  if (!channel || !agent)
    return <ErrorPanel error={new AccessError('notFound')} />;
  return (
    <>
      <Link className={styles.link} to={`${basePath}/channels`}>
        {t('nav.channels')}
      </Link>
      <h1 dir="auto">{channel.name}</h1>
      <Active value={channel.active} />
      <dl className={styles.facts}>
        <div>
          <dt>{t('intelligence.channelType')}</dt>
          <dd>{t(`intelligence.channel.${channel.type}`)}</dd>
        </div>
        <div>
          <dt>{t('intelligence.agent')}</dt>
          <dd>
            <Link className={styles.link} to={`${basePath}/agents/${agent.id}`}>
              <bdi>{agent.name}</bdi>
            </Link>
          </dd>
        </div>
        <div>
          <dt>{t('intelligence.created')}</dt>
          <dd>
            <time dateTime={channel.createdAt}>{date(channel.createdAt)}</time>
          </dd>
        </div>
        <div>
          <dt>{t('intelligence.updated')}</dt>
          <dd>
            <time dateTime={channel.updatedAt}>{date(channel.updatedAt)}</time>
          </dd>
        </div>
      </dl>
      <p className={styles.notice}>{t('intelligence.channelBoundary')}</p>
      {company.permissions.includes('tenant.conversations.read') && (
        <Link className={styles.link} to={`${basePath}/conversations`}>
          {t('nav.conversations')}
        </Link>
      )}
    </>
  );
}

/** Pagination follows skip/limit projections; no real-time or send action is exposed. */
export function ConversationsPage(): ReactElement {
  const { t } = useTranslation();
  const adapter = useAdapter();
  const { scope, intelligenceKey, basePath } = useIntelligence();
  const agents = useAgentWorkspace();
  const { date } = useBusinessFormatting();
  const [filter, setFilter] = useState<ConversationFilter>({
    query: '',
    agentId: null,
    status: 'all',
    skip: 0,
  });
  const query = useQuery({
    queryKey: [...intelligenceKey, 'conversations', filter],
    queryFn: ({ signal }) => adapter.conversations(scope, filter, signal),
    retry: false,
  });
  return (
    <>
      <h1>{t('nav.conversations')}</h1>
      <p>{t('intelligence.conversationIntro')}</p>
      <div className={styles.filters}>
        <label className={shared.field}>
          {t('intelligence.search')}
          <input
            type="search"
            maxLength={100}
            value={filter.query}
            onChange={(event) =>
              setFilter({ ...filter, query: event.target.value, skip: 0 })
            }
          />
        </label>
        <label className={shared.field}>
          {t('intelligence.status')}
          <select
            value={filter.status}
            onChange={(event) =>
              setFilter({
                ...filter,
                status: event.target.value as ConversationFilter['status'],
                skip: 0,
              })
            }
          >
            <option value="all">{t('intelligence.all')}</option>
            {conversationStatuses.map((value) => (
              <option key={value} value={value}>
                {t(`intelligence.status.${value}`)}
              </option>
            ))}
          </select>
        </label>
        <label className={shared.field}>
          {t('intelligence.agent')}
          <select
            value={filter.agentId ?? ''}
            onChange={(event) =>
              setFilter({
                ...filter,
                agentId: event.target.value ? Number(event.target.value) : null,
                skip: 0,
              })
            }
          >
            <option value="">{t('intelligence.all')}</option>
            {agents.data?.agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {query.isPending ? (
        <LoadingPanel />
      ) : query.isError ? (
        <ErrorPanel error={query.error} retry={() => void query.refetch()} />
      ) : (
        <>
          {query.data.items.length === 0 ? (
            <EmptyResults
              clear={() =>
                setFilter({ query: '', agentId: null, status: 'all', skip: 0 })
              }
            />
          ) : (
            <ul className={styles.list}>
              {query.data.items.map((row) => (
                <li className={styles.row} key={row.id}>
                  <h2 dir="auto">
                    {row.userName ?? t('intelligence.visitor')}
                  </h2>
                  <Badge>{t(`intelligence.status.${row.status}`)}</Badge>
                  <p>
                    <time dateTime={row.updatedAt}>{date(row.updatedAt)}</time>{' '}
                    · <bdi>{row.userId}</bdi>
                  </p>
                  <Link
                    className={styles.link}
                    to={`${basePath}/conversations/${row.id}`}
                  >
                    {t('intelligence.openConversation')} ·{' '}
                    <bdi>{row.userName ?? row.userId}</bdi>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Pager
            skip={query.data.skip}
            total={query.data.total}
            limit={query.data.limit}
            change={(skip) => setFilter({ ...filter, skip })}
          />
        </>
      )}
    </>
  );
}

/** Bounded chronological pages render untrusted content as escaped text, including media references. */
export function ConversationDetailPage(): ReactElement {
  const { t } = useTranslation();
  const { conversationId } = useParams();
  const id = positiveId(conversationId);
  const { scope, intelligenceKey, basePath } = useIntelligence();
  const adapter = useAdapter();
  const { date } = useBusinessFormatting();
  const [skip, setSkip] = useState(0);
  useEffect(() => setSkip(0), [id]);
  const conversation = useQuery({
    queryKey: [...intelligenceKey, 'conversation', id],
    queryFn: ({ signal }) => adapter.conversation(scope, id ?? 0, signal),
    enabled: id !== null,
    retry: false,
  });
  const messages = useQuery({
    queryKey: [...intelligenceKey, 'messages', id, skip],
    queryFn: ({ signal }) => adapter.messages(scope, id ?? 0, skip, signal),
    enabled: Boolean(conversation.data),
    retry: false,
  });
  if (id === null) return <ErrorPanel error={new AccessError('notFound')} />;
  if (conversation.isError)
    return (
      <ErrorPanel
        error={conversation.error}
        retry={() => void conversation.refetch()}
      />
    );
  if (conversation.isPending) return <LoadingPanel />;
  const row = conversation.data;
  return (
    <>
      <Link className={styles.link} to={`${basePath}/conversations`}>
        {t('nav.conversations')}
      </Link>
      <h1 dir="auto">{row.userName ?? t('intelligence.visitor')}</h1>
      <Badge>{t(`intelligence.status.${row.status}`)}</Badge>
      <dl className={styles.facts}>
        <div>
          <dt>{t('intelligence.participant')}</dt>
          <dd>
            <bdi>{row.userId}</bdi>
          </dd>
        </div>
        <div>
          <dt>{t('intelligence.created')}</dt>
          <dd>
            <time dateTime={row.createdAt}>{date(row.createdAt)}</time>
          </dd>
        </div>
        <div>
          <dt>{t('intelligence.agent')}</dt>
          <dd>
            <Link
              className={styles.link}
              to={`${basePath}/agents/${row.agentId}`}
            >
              #{row.agentId}
            </Link>
          </dd>
        </div>
        <div>
          <dt>{t('nav.channels')}</dt>
          <dd>
            <Link
              className={styles.link}
              to={`${basePath}/channels/${row.channelId}`}
            >
              #{row.channelId}
            </Link>
          </dd>
        </div>
      </dl>
      <h2>{t('intelligence.messages')}</h2>
      {messages.isPending ? (
        <LoadingPanel />
      ) : messages.isError ? (
        <ErrorPanel
          error={messages.error}
          retry={() => void messages.refetch()}
        />
      ) : (
        <>
          {messages.data.items.length === 0 ? (
            <p>{t('intelligence.emptyMessages')}</p>
          ) : (
            <ol
              className={styles.messages}
              aria-label={t('intelligence.messages')}
              start={messages.data.skip + 1}
            >
              {messages.data.items.map((message) => (
                <li
                  className={styles.message}
                  data-role={message.role}
                  key={message.id}
                >
                  <div className={styles.messageHeader}>
                    <strong>{t(`intelligence.role.${message.role}`)}</strong>
                    <time dateTime={message.createdAt}>
                      {date(message.createdAt)}
                    </time>
                  </div>
                  {message.contentType !== 'text' && (
                    <p>
                      {t('intelligence.mediaBoundary')} ·{' '}
                      {t(`intelligence.media.${message.contentType}`)}
                    </p>
                  )}
                  <p className={styles.content} dir="auto">
                    {message.content}
                  </p>
                </li>
              ))}
            </ol>
          )}
          <Pager
            skip={messages.data.skip}
            total={messages.data.total}
            limit={messages.data.limit}
            change={setSkip}
          />
        </>
      )}
      <p className={styles.notice}>{t('intelligence.readOnly')}</p>
    </>
  );
}
