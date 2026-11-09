// MoulAI™ — read-only history pages; no fallback to a truncated or synthetic journal.
import { z } from 'zod';
import type { LocalDiningClient, LocalScope } from './client';

const event = z.object({
  id: z.number().int().positive(),
  kind: z.string(),
  occurred_at: z.string(),
  request_id: z.number().int().positive().nullable(),
  author_key: z.string(),
  author_name: z.string().nullable(),
  author_name_source: z.literal('current_profile').nullable(),
  details: z.record(z.unknown()),
});
const page = z.object({
  items: z.array(event),
  total: z.number().int().nonnegative(),
  page: z.number().int().positive(),
  page_size: z.number().int().positive(),
  snapshot_id: z.number().int().nonnegative(),
  kinds: z.array(z.string()),
  authors: z.array(z.object({ key: z.string(), name: z.string().nullable() })),
  authors_truncated: z.boolean(),
});
export type HistoryEvent = z.infer<typeof event>;
export type HistoryPage = z.infer<typeof page>;
export interface HistoryFilter {
  from: string;
  until: string;
  kind: string;
  author: string;
  page: number;
  snapshot?: number;
}
export async function readHistory(
  api: LocalDiningClient,
  scope: LocalScope,
  filter: HistoryFilter,
): Promise<HistoryPage> {
  const query = new URLSearchParams({
    page: String(filter.page),
    page_size: '20',
  });
  if (filter.from) query.set('from_day', filter.from);
  if (filter.until) query.set('until_day', filter.until);
  if (filter.kind) query.set('kind', filter.kind);
  if (filter.author) query.set('author', filter.author);
  if (filter.snapshot !== undefined)
    query.set('snapshot_id', String(filter.snapshot));
  return page.parse(await api.request(api.root(scope) + '/events?' + query));
}
