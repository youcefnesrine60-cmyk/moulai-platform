// MoulAI™ — local presentation events, never business commands or transport messages.
export interface HelpRequest {
  mode: 'guide' | 'assistant';
  operation?: string;
  field?: boolean;
  elementId?: string;
}
export const HELP_EVENT = 'moulai-dining-help';
export function requestDiningHelp(request: HelpRequest): void {
  window.dispatchEvent(
    new CustomEvent<HelpRequest>(HELP_EVENT, { detail: request }),
  );
}
