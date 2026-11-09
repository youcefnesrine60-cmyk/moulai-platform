// MoulAI™ — local, non-generative guidance over versioned documentation. No business/API client.
import { z } from 'zod';
import { d1Fr } from '../../i18n/d1.fr';
import { serviceFr } from '../../i18n/diningService';
import {
  GUIDE_VERSION,
  procedures,
  topicForOperation,
  topicForSection,
  type Topic,
} from './documentation';

const capabilities = [
  'read',
  'configure',
  'service',
  'clean',
  'collect',
  'assistant',
  'reservations.cancel_before_arrival',
  'finance.read',
  'invoices.create',
  'invoices.finalize',
  'advances.allocate',
  'orders.read',
  'orders.approve',
  'orders.prepare',
  'orders.complete',
  'documents.issue',
] as const;
const sections = [
  'planning',
  'configuration',
  'staff',
  'requests',
  'visits',
  'finance',
  'history',
  'unscoped',
] as const;
const errors = [
  'dining_actual_vacancy_required_for_installation',
  'dining_policy_configuration_missing',
  'dining_explicit_capability_required',
  'dining_active_hold_required',
  'dining_verified_matching_receipt_required',
  'dining_receipt_amount_or_currency_mismatch',
  'dining_early_arrival_requires_explicit_policy',
  'dining_actual_occupation_period_invalid',
  'dining_resource_unavailable',
] as const;
const labels = new Set([...Object.keys(d1Fr), ...Object.keys(serviceFr)]);
const operations = new Set(procedures.flatMap((item) => item.operations));
const control = z.object({
  labelKey: z.string().refine((key) => labels.has('d1.' + key)),
  type: z.enum([
    'text',
    'number',
    'date',
    'time',
    'datetime-local',
    'select',
    'checkbox',
    'button',
    'textarea',
  ]),
  required: z.boolean(),
  disabled: z.boolean(),
  invalid: z.boolean(),
  operation: z
    .string()
    .refine((key) => operations.has(key))
    .optional(),
});
const context = z.object({
  section: z.enum(sections),
  role: z.enum(['owner', 'manager', 'employee', 'none']),
  capabilities: z.array(z.enum(capabilities)).max(capabilities.length),
  permissionsKnown: z.boolean(),
  policyPresent: z.boolean().nullable(),
  tableState: z
    .enum(['available', 'occupied', 'dirty', 'maintenance', 'out_of_service'])
    .nullable(),
  busy: z.boolean(),
  errorCode: z.enum(errors).nullable(),
  control: control.nullable(),
});
export type SafeHelpContext = z.infer<typeof context>;
export type ControlContext = z.infer<typeof control>;
export function safeHelpContext(input: {
  section: string;
  role: string;
  capabilities: readonly string[];
  permissionsKnown: boolean;
  policyPresent: boolean | null;
  tableState: string | null;
  busy: boolean;
  errorCode?: string | null;
  control?: ControlContext | null;
}): SafeHelpContext {
  // Rebuild a closed projection. Additional properties, tenant IDs, form values and tokens are discarded.
  return context.parse({
    section: sections.includes(input.section as (typeof sections)[number])
      ? input.section
      : 'unscoped',
    role: ['owner', 'manager', 'employee'].includes(input.role)
      ? input.role
      : 'none',
    capabilities: [
      ...new Set(
        input.capabilities.filter(
          (item): item is (typeof capabilities)[number] =>
            capabilities.includes(item as (typeof capabilities)[number]),
        ),
      ),
    ],
    permissionsKnown: input.permissionsKnown,
    policyPresent: input.policyPresent,
    tableState: [
      'available',
      'occupied',
      'dirty',
      'maintenance',
      'out_of_service',
    ].includes(input.tableState ?? '')
      ? input.tableState
      : null,
    busy: input.busy,
    errorCode: errors.includes(input.errorCode as (typeof errors)[number])
      ? input.errorCode
      : null,
    control: control.safeParse(input.control).success
      ? control.parse(input.control)
      : null,
  });
}
export interface AnswerPlan {
  source: 'local-documentation';
  version: string;
  topic: Topic;
  notices: readonly string[];
  clarification: boolean;
}
function normalized(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f\u064b-\u065f]/g, '');
}
export function explainLocally(
  question: string,
  current: SafeHelpContext,
): AnswerPlan {
  const text = normalized(question);
  const topics: Topic[] = [];
  if (/reserv|booking|حجز/.test(text)) topics.push('reservations');
  if (/instal|arriv|seat|walk.?in|اجلاس|جلوس|تركيب/.test(text))
    topics.push('walkin');
  if (/nettoy|clean|depart|تنظيف|مغادر/.test(text)) topics.push('cleaning');
  if (
    /factur|paie|encaiss|invoice|payment|collect|فاتور|دفع|تحصيل|عربون/.test(
      text,
    )
  )
    topics.push('finance');
  if (/command|cuisin|order|kitchen|طلب|مطبخ/.test(text)) topics.push('orders');
  if (/\bqr\b|scan|رمز|مسح|visit|زيار/.test(text)) topics.push('qr');
  if (
    /personnel|\bfonctions?\b|autoris|employ|staff|permission|موظف|صلاحي|وظيف/.test(
      text,
    )
  )
    topics.push('staff');
  if (/config|horaire|tarif|opening|اعداد|تعريف|ساعات/.test(text))
    topics.push('configuration');
  if (/journal|evenement|histor|audit|حدث|سجل/.test(text))
    topics.push('history');
  if (/difference|notion|concept|statut|status|فرق|حالة/.test(text))
    topics.splice(0, topics.length, 'concepts');
  if (/champ|field|button|bouton|حقل|زر/.test(text) && current.control)
    topics.splice(
      0,
      topics.length,
      topicForOperation(current.control.operation ?? ''),
    );
  const unique = [...new Set(topics)];
  let topic = unique[0] ?? topicForSection(current.section);
  const notices: string[] = [];
  let clarification = unique.length !== 1;
  if (!question.trim() || question.length > 600) {
    notices.push('help.tooLong');
    clarification = true;
  } else if (unique.length > 1) notices.push('help.ambiguous');
  else if (!unique.length)
    notices.push(
      /confirm|valider|تاكيد/.test(text) ? 'help.ambiguous' : 'help.unknown',
    );
  if (current.busy) notices.push('help.busy');
  if (current.control?.disabled) notices.push('help.disabled');
  if (topic === 'walkin' && !clarification) {
    if (current.permissionsKnown && !current.capabilities.includes('service'))
      notices.push('help.missingService');
    if (current.policyPresent === false) notices.push('help.noPolicy');
    if (current.tableState === null) {
      notices.push('help.chooseTable');
      clarification = true;
    } else if (current.tableState !== 'available')
      notices.push('help.notVacant');
    else notices.push('help.cannotCertify');
  }
  const errorTopics: Record<(typeof errors)[number], [Topic, string]> = {
    dining_actual_vacancy_required_for_installation: [
      'walkin',
      'help.notVacant',
    ],
    dining_policy_configuration_missing: ['configuration', 'help.noPolicy'],
    dining_explicit_capability_required: ['staff', 'help.errPermission'],
    dining_active_hold_required: ['reservations', 'help.errHold'],
    dining_verified_matching_receipt_required: ['finance', 'help.errReceipt'],
    dining_receipt_amount_or_currency_mismatch: ['finance', 'help.errMoney'],
    dining_early_arrival_requires_explicit_policy: ['walkin', 'help.errEarly'],
    dining_actual_occupation_period_invalid: ['walkin', 'help.errPeriod'],
    dining_resource_unavailable: ['concepts', 'help.errResource'],
  };
  if (
    current.errorCode &&
    /erreur|error|proble|blocked|disabled|bloqu|خطا|مشكل|متعذر/.test(text)
  ) {
    const item = errorTopics[current.errorCode];
    topic = item[0];
    notices.push(item[1]);
    clarification = false;
  }
  return {
    source: 'local-documentation',
    version: GUIDE_VERSION,
    topic,
    notices: [...new Set(notices)],
    clarification,
  };
}

/** An optional selector can only select existing documents, never emit claims or actions.
 * No provider transport is installed or imported by the UI. These contracts are tested with in-process fakes.
 */
export interface DocumentationSelector {
  select(
    request: Readonly<{
      version: string;
      intent: Topic;
      context: SafeHelpContext;
      allowedTopics: readonly Topic[];
    }>,
    signal: AbortSignal,
  ): Promise<unknown>;
}
const selection = z
  .object({
    version: z.literal(GUIDE_VERSION),
    topics: z
      .array(
        z.enum([
          'start',
          'configuration',
          'staff',
          'reservations',
          'walkin',
          'qr',
          'orders',
          'finance',
          'cleaning',
          'history',
          'concepts',
        ]),
      )
      .min(1)
      .max(3),
    clarify: z.boolean(),
  })
  .strict();
export async function boundedDocumentSelection(input: {
  selector?: DocumentationSelector;
  current: SafeHelpContext;
  fallback: AnswerPlan;
  timeoutMs?: number;
  signal?: AbortSignal;
}): Promise<{ plan: AnswerPlan; selectionUsed: boolean; fallback: boolean }> {
  if (!input.selector)
    return { plan: input.fallback, selectionUsed: false, fallback: true };
  const abort = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const cancel = () => abort.abort();
  input.signal?.addEventListener('abort', cancel, { once: true });
  try {
    if (input.signal?.aborted) throw new Error('Selection cancelled');
    const request = {
      version: GUIDE_VERSION,
      intent: input.fallback.topic,
      context: context.parse(input.current),
      allowedTopics: procedures.map((item) => item.id),
    };
    const response = await Promise.race([
      input.selector.select(request, abort.signal),
      new Promise<never>((_, reject) => {
        timer = setTimeout(
          () => {
            abort.abort();
            reject(new Error('Selection timeout'));
          },
          Math.min(Math.max(input.timeoutMs ?? 8000, 1), 8000),
        );
      }),
      new Promise<never>((_, reject) =>
        abort.signal.addEventListener(
          'abort',
          () => reject(new Error('Selection cancelled')),
          { once: true },
        ),
      ),
    ]);
    if (JSON.stringify(response).length > 2048)
      throw new Error('Selection too large');
    const parsed = selection.parse(response);
    return {
      plan: {
        ...input.fallback,
        topic: parsed.topics[0]!,
        clarification: parsed.clarify,
      },
      selectionUsed: true,
      fallback: false,
    };
  } catch {
    return {
      plan: {
        ...input.fallback,
        notices: [...input.fallback.notices, 'help.fallback'],
      },
      selectionUsed: false,
      fallback: true,
    };
  } finally {
    if (timer) clearTimeout(timer);
    abort.abort();
    input.signal?.removeEventListener('abort', cancel);
  }
}

export class LocalHelpLimit {
  private calls: number[] = [];
  private count = 0;
  admit(now = Date.now()): boolean {
    this.calls = this.calls.filter((time) => now - time < 60000);
    if (this.count >= 30 || this.calls.length >= 10) return false;
    this.calls.push(now);
    this.count++;
    return true;
  }
}
