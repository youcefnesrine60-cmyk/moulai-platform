// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

/** Generated from closed Pydantic contracts. Decimal inputs intentionally use strings. */
export type AllocationOperation = {
  readonly operation: 'allocate';
  readonly invoice_id: number;
  readonly receipt_id: number;
};

export type ArrivalOperation = {
  readonly operation: 'arrival';
  readonly request_id: number | null;
  readonly table_ids: ReadonlyArray<number>;
  readonly party_size: number;
  readonly expected_end: string;
};

export type BlackoutOperation = {
  readonly operation: 'blackout';
  readonly starts_at: string;
  readonly ends_at: string;
  readonly kind: 'closure' | 'maintenance' | 'preparation' | 'cleaning';
  readonly reason: string;
  readonly table_id?: number | null;
  readonly zone_id?: number | null;
  readonly acknowledge_conflicts?: boolean;
};

export type CalendarOperation = {
  readonly operation: 'calendar';
  readonly weekday?: number | null;
  readonly service_date?: string | null;
  readonly windows: ReadonlyArray<OpeningWindow>;
  readonly acknowledge_conflicts?: boolean;
};

export type CancelOperation = {
  readonly operation: 'cancel_before_arrival';
  readonly request_id: number;
  readonly reason: string;
  readonly origin: 'human' | 'customer' | 'assistant';
};

export type CloseBlackoutOperation = {
  readonly operation: 'close_blackout';
  readonly identifier: number;
};

export type CombinationInput = {
  readonly code: string;
  readonly table_ids: ReadonlyArray<number>;
  readonly min_capacity: number;
  readonly max_capacity: number;
  readonly pricing_ref: string;
  readonly active: boolean;
};

export type CombinationOperation = {
  readonly operation: 'combination';
  readonly identifier?: number | null;
  readonly acknowledge_conflicts?: boolean;
  readonly data: CombinationInput;
};

export type DeadlineOperation = {
  readonly operation: 'scan_deadlines';
};

export type DiningPolicyInput = {
  readonly timezone: string;
  readonly response_seconds: number;
  readonly hold_seconds: number;
  readonly lateness_seconds: number;
  readonly preparation_seconds: number;
  readonly cleaning_seconds: number;
  readonly confirmation_seconds: number;
  readonly confirmation_scope: 'tables';
  readonly alert_offsets_seconds: ReadonlyArray<number>;
  readonly service_recipients: ReadonlyArray<number>;
  readonly escalation_recipients: ReadonlyArray<number>;
  readonly currencies: Readonly<Record<string, number>>;
  readonly payment_instructions: Readonly<Record<string, string>>;
  readonly terms: string;
};

export type ExtensionOperation = {
  readonly operation: 'extend';
  readonly occupation_id: number;
  readonly expected_end: string;
};

export type FinalizeOperation = {
  readonly operation: 'confirm_human' | 'confirm_assistant';
  readonly request_id: number;
  readonly quote_id: number;
  readonly receipt_id: number;
};

export type GrantOperation = {
  readonly operation: 'grant';
  readonly membership_id: number;
  readonly capability:
    | 'read'
    | 'service'
    | 'clean'
    | 'collect'
    | 'assistant'
    | 'reservations.cancel_before_arrival'
    | 'finance.read'
    | 'invoices.create'
    | 'invoices.finalize'
    | 'advances.allocate'
    | 'orders.read'
    | 'orders.approve'
    | 'orders.prepare'
    | 'orders.complete'
    | 'documents.issue';
  readonly actor_kind: 'human' | 'assistant';
  readonly active: boolean;
};

export type HoldOperation = {
  readonly operation: 'hold';
  readonly request_id: number;
  readonly quote_id: number;
};

export type InvoiceFinalizeOperation = {
  readonly operation: 'finalize_invoice';
  readonly invoice_id: number;
  readonly expected_revision: number;
};

export type InvoiceInput = {
  readonly request_id?: number | null;
  readonly occupation_id?: number | null;
  readonly currency: string;
  readonly lines: ReadonlyArray<InvoiceLineInput>;
  readonly currency_source: string;
  readonly rounding_source: string;
  readonly reconciliation_reference: string;
  readonly legacy_discrepancies_acknowledged: boolean;
};

export type InvoiceLineInput = {
  readonly order_id: number;
  readonly order_item_id: number;
  readonly description: string;
  readonly quantity: string;
  readonly unit_price: string;
  readonly source_reference: string;
};

export type InvoiceOperation = {
  readonly operation: 'invoice';
  readonly data: InvoiceInput;
};

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | ReadonlyArray<JsonValue>
  | { readonly [key: string]: JsonValue };

export type MenuItemInput = {
  readonly product_id: number;
  readonly quantity: string;
};

export type OpeningWindow = {
  readonly start: string;
  readonly end: string;
  readonly next_day: boolean;
  readonly start_fold?: 0 | 1 | null;
  readonly end_fold?: 0 | 1 | null;
};

export type PhysicalOperation = {
  readonly operation: 'departure' | 'start_cleaning' | 'finish_cleaning';
  readonly occupation_id: number;
};

export type PolicyOperation = {
  readonly operation: 'policy';
  readonly data: DiningPolicyInput;
};

export type ProofOperation = {
  readonly operation: 'human_proof';
  readonly request_id?: number | null;
  readonly table_ids: ReadonlyArray<number>;
  readonly starts_at: string;
  readonly ends_at: string;
};

export type QuoteOperation = {
  readonly operation: 'quote';
  readonly request_id: number;
  readonly currency: string;
  readonly expires_at: string;
};

export type ReferenceInput = {
  readonly kind:
    | 'shape'
    | 'category'
    | 'zone'
    | 'location'
    | 'view'
    | 'proximity'
    | 'feature'
    | 'event';
  readonly code: string;
  readonly labels: Readonly<Record<string, string>>;
  readonly active: boolean;
  readonly pricing_ref?: string | null;
};

export type ReferenceOperation = {
  readonly operation: 'reference';
  readonly identifier?: number | null;
  readonly acknowledge_conflicts?: boolean;
  readonly data: ReferenceInput;
};

export type RequestInput = {
  readonly customer_name: string;
  readonly contact: string;
  readonly starts_at: string;
  readonly duration_seconds: number;
  readonly party_size: number;
  readonly table_ids: ReadonlyArray<number>;
  readonly criteria: Readonly<Record<string, JsonValue>>;
  readonly event_id?: number | null;
  readonly preparation: boolean;
  readonly menu: ReadonlyArray<MenuItemInput>;
};

export type RequestOperation = {
  readonly operation: 'request';
  readonly data: RequestInput;
};

export type RestaurantConsentOperation = {
  readonly operation: 'restaurant_consent';
  readonly quote_id: number;
  readonly digest: string;
};

export type SelectOperation = {
  readonly operation: 'select_tables';
  readonly request_id: number;
  readonly table_ids: ReadonlyArray<number>;
};

export type SignalOperation = {
  readonly operation: 'signal';
  readonly reason: string;
  readonly request_id: number;
  readonly kind:
    | 'customer_departure'
    | 'customer_cancellation_requested'
    | 'late_arrival'
    | 'expected_end_passed';
};

export type StateOperation = {
  readonly operation: 'physical_state';
  readonly table_id: number;
  readonly state: 'available' | 'maintenance' | 'out_of_service';
};

export type TableInput = {
  readonly code: string;
  readonly name?: string | null;
  readonly min_capacity: number;
  readonly max_capacity: number;
  readonly shape_id: number;
  readonly category_id: number;
  readonly zone_id: number;
  readonly location_id: number;
  readonly description: string;
  readonly floor_label?: string | null;
  readonly room_label?: string | null;
  readonly photos: ReadonlyArray<string>;
  readonly pricing_ref: string;
  readonly in_service: boolean;
  readonly trait_ids: ReadonlyArray<number>;
};

export type TableOperation = {
  readonly operation: 'table';
  readonly identifier?: number | null;
  readonly initial_state?:
    'available' | 'maintenance' | 'out_of_service' | null;
  readonly acknowledge_conflicts?: boolean;
  readonly data: TableInput;
};

export type TariffInput = {
  readonly reference: string;
  readonly component: 'table' | 'preparation' | 'menu';
  readonly currency: string;
  readonly unit: 'per_hour' | 'flat' | 'per_person' | 'per_item';
  readonly unit_price: string;
  readonly valid_from: string;
  readonly valid_until: string | null;
};

export type TariffOperation = {
  readonly operation: 'tariff';
  readonly data: TariffInput;
};

export type DiningOperation =
  | PolicyOperation
  | ReferenceOperation
  | TableOperation
  | CombinationOperation
  | CalendarOperation
  | TariffOperation
  | GrantOperation
  | BlackoutOperation
  | CloseBlackoutOperation
  | RequestOperation
  | SelectOperation
  | ProofOperation
  | QuoteOperation
  | RestaurantConsentOperation
  | HoldOperation
  | FinalizeOperation
  | ArrivalOperation
  | PhysicalOperation
  | ExtensionOperation
  | StateOperation
  | SignalOperation
  | CancelOperation
  | InvoiceOperation
  | InvoiceFinalizeOperation
  | AllocationOperation
  | DeadlineOperation;
