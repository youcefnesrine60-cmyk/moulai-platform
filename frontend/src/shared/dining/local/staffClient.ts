// MoulAI™ — typed professional commands use the same authenticated local transport.
import { z } from 'zod';
import type { LocalDiningClient, LocalScope, OperationResult } from './client';
export type StaffCommand =
  | {
      operation: 'invite';
      issuer: string;
      subject: string;
      employee_code: string;
      display_name: string;
    }
  | {
      operation: 'profile';
      membership_id: number;
      employee_code: string;
      display_name: string;
    }
  | {
      operation: 'function';
      code: string;
      labels: { fr: string; en: string; ar: string };
      tasks: string[];
      active: boolean;
    }
  | {
      operation: 'assignment';
      membership_id: number;
      function_id: number;
      active: boolean;
    }
  | {
      operation: 'status';
      membership_id: number;
      expected_revision: number;
      status: 'active' | 'suspended' | 'revoked';
      reason: string;
    };
const result = z.object({
  identifier: z.number().int().positive(),
  operation: z.string(),
});
const invitation = z.object({
  organization_id: z.number(),
  membership_id: z.number(),
  organization_name: z.string(),
  restaurant_id: z.number(),
  branch_id: z.number(),
  employee_code: z.string(),
  display_name: z.string(),
  accepted: z.boolean(),
  status: z.string(),
});
export type StaffInvitation = z.infer<typeof invitation>;
export async function submitStaff(
  api: LocalDiningClient,
  scope: LocalScope,
  command: StaffCommand,
): Promise<OperationResult> {
  return result.parse(
    await api.request(api.root(scope) + '/staff', 'POST', command),
  );
}
export async function ownInvitations(
  api: LocalDiningClient,
): Promise<StaffInvitation[]> {
  return z
    .array(invitation)
    .parse(await api.request('/local-d1/dining/employment/invitations'));
}
export async function acceptEmployment(
  api: LocalDiningClient,
  row: StaffInvitation,
): Promise<void> {
  z.object({
    membership_id: z.number(),
    status: z.literal('pending_owner_activation'),
  }).parse(
    await api.request(
      `/local-d1/dining/employment/${row.organization_id}/${row.membership_id}/accept`,
      'POST',
      {},
    ),
  );
}
