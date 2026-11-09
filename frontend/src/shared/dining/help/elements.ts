// MoulAI™ — explicit element selection; values, credentials and arbitrary DOM text are never read.
import { d1Fr } from '../../i18n/d1.fr';
import { serviceFr } from '../../i18n/diningService';
import { procedures } from './documentation';
export type ElementKind =
  'field' | 'button' | 'select' | 'toggle' | 'choice' | 'group' | 'other';
export interface SelectedElement {
  labelKey: string;
  kind: ElementKind;
  operation: string | null;
  action: string | null;
  required: boolean;
  invalid: boolean;
  disabled: boolean;
  disabledReason: 'busy' | 'fixedReference' | null;
}
const labels = new Set([...Object.keys(d1Fr), ...Object.keys(serviceFr)]);
const operations = new Set(procedures.flatMap((item) => item.operations));
/** Accept only explicit element IDs and static translation keys; never infer from previous focus. */
export function readSelectedElement(
  id: string | undefined,
): SelectedElement | null {
  if (!id || id.length > 160) return null;
  const node = document.getElementById(id);
  if (!node || !node.isConnected) return null;
  const labelKey = node.dataset.helpLabel;
  if (!labelKey || !labels.has('d1.' + labelKey)) return null;
  const native =
    node instanceof HTMLInputElement ||
    node instanceof HTMLSelectElement ||
    node instanceof HTMLTextAreaElement;
  const kind: ElementKind =
    node instanceof HTMLButtonElement
      ? 'button'
      : node instanceof HTMLSelectElement
        ? 'select'
        : node instanceof HTMLTextAreaElement
          ? 'field'
          : node instanceof HTMLInputElement
            ? node.type === 'checkbox'
              ? 'toggle'
              : node.type === 'radio'
                ? 'choice'
                : ['text', 'number', 'date', 'time', 'datetime-local'].includes(
                      node.type,
                    )
                  ? 'field'
                  : 'other'
            : node instanceof HTMLFieldSetElement ||
                node.getAttribute('role') === 'radiogroup'
              ? 'group'
              : 'other';
  if (
    node instanceof HTMLInputElement &&
    ['password', 'file', 'hidden'].includes(node.type)
  )
    return null;
  const form = node.closest<HTMLFormElement>('form[data-operation]'),
    op = form?.dataset.operation;
  const disabled = node.matches(':disabled');
  return {
    labelKey,
    kind,
    operation: op && operations.has(op) ? op : null,
    action: ['session-open', 'session-close'].includes(
      node.dataset.helpAction ?? '',
    )
      ? (node.dataset.helpAction ?? null)
      : null,
    required: native && kind !== 'button' ? node.required : false,
    invalid: native && !node.validity.valid,
    disabled,
    disabledReason:
      disabled && node.closest('[data-help-busy="true"]')
        ? 'busy'
        : disabled && node.dataset.helpDisabled === 'fixedReference'
          ? 'fixedReference'
          : null,
  };
}
export type ElementRule =
  | 'reference'
  | 'table'
  | 'policy'
  | 'calendar'
  | 'tariff'
  | 'grant'
  | 'combination'
  | 'blackout'
  | 'staff'
  | 'staffInvite'
  | 'staffProfile'
  | 'staffFunction'
  | 'staffAssignment'
  | 'staffStatus'
  | 'request'
  | 'selection'
  | 'quote'
  | 'hold'
  | 'consent'
  | 'proof'
  | 'confirm'
  | 'arrival'
  | 'physical'
  | 'extension'
  | 'cancel'
  | 'signal'
  | 'receipt'
  | 'invoice'
  | 'finalize'
  | 'allocation'
  | 'qr'
  | 'presence'
  | 'order'
  | 'sessionOpen'
  | 'sessionClose'
  | 'profile'
  | 'branch'
  | 'code'
  | 'labels'
  | 'customer'
  | 'capacity'
  | 'period'
  | 'money'
  | 'currency'
  | 'observation'
  | 'conflicts'
  | 'active'
  | 'referenceKind'
  | 'edit'
  | 'scopeChoice'
  | 'identity'
  | 'reason'
  | 'permission'
  | 'pricing'
  | 'state';
const operationRules: Readonly<Record<string, ElementRule>> = {
  reference: 'reference',
  table: 'table',
  policy: 'policy',
  calendar: 'calendar',
  tariff: 'tariff',
  grant: 'grant',
  combination: 'combination',
  blackout: 'blackout',
  staff_invite: 'staffInvite',
  staff_profile: 'staffProfile',
  staff_function: 'staffFunction',
  staff_assignment: 'staffAssignment',
  staff_status: 'staffStatus',
  request: 'request',
  select_tables: 'selection',
  quote: 'quote',
  hold: 'hold',
  customer_consent: 'consent',
  restaurant_consent: 'consent',
  human_proof: 'proof',
  confirm_human: 'confirm',
  confirm_assistant: 'confirm',
  arrival: 'arrival',
  physical: 'physical',
  physical_state: 'physical',
  extend: 'extension',
  cancel_before_arrival: 'cancel',
  customer_cancellation: 'cancel',
  signal: 'signal',
  receipt: 'receipt',
  invoice: 'invoice',
  finalize_invoice: 'finalize',
  allocate: 'allocation',
  public_link: 'qr',
  install_presence: 'presence',
  visit_order_transition: 'order',
};
const fieldRules: Readonly<Record<string, ElementRule>> = {
  testProfile: 'profile',
  authorizedBranch: 'branch',
  code: 'code',
  employeeCode: 'code',
  functionCode: 'code',
  fr: 'labels',
  en: 'labels',
  ar: 'labels',
  customerName: 'customer',
  party: 'capacity',
  partySize: 'capacity',
  minimum: 'capacity',
  maximum: 'capacity',
  minCapacity: 'capacity',
  maxCapacity: 'capacity',
  referenceKind: 'referenceKind',
  editOrCreate: 'edit',
  table: 'scopeChoice',
  tables: 'scopeChoice',
  reservation: 'scopeChoice',
  person: 'scopeChoice',
  request: 'scopeChoice',
  physicalAction: 'physical',
  currency: 'currency',
  observed: 'observation',
  humanObserved: 'observation',
  ackConflicts: 'conflicts',
  active: 'active',
  reason: 'reason',
  issuer: 'identity',
  subject: 'identity',
  capability: 'permission',
  actorKind: 'permission',
  pricingRef: 'pricing',
  initialState: 'state',
  state: 'state',
  expectedEnd: 'period',
  start: 'period',
  end: 'period',
  date: 'period',
  amount: 'money',
  receivedAmount: 'money',
  expectedAmount: 'money',
  unitPrice: 'money',
};
/** A missing entry is deliberately unexplained; metadata alone is not a functional diagnosis. */
export function elementRule(element: SelectedElement): ElementRule | null {
  if (element.kind === 'other') return null;
  if (element.kind === 'button')
    return element.action === 'session-open'
      ? 'sessionOpen'
      : element.action === 'session-close'
        ? 'sessionClose'
        : element.operation
          ? (operationRules[element.operation] ?? null)
          : null;
  return fieldRules[element.labelKey] ?? null;
}
