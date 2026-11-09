// MoulAI™ — professional records are separate from capabilities and account credentials.
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { localized } from '../../../shared/i18n';
import { Button } from '../../../shared/ui/primitives';
import type { LocalDiningClient } from '../../../shared/dining/local/client';
import {
  submitStaff,
  ownInvitations,
  acceptEmployment,
  type StaffInvitation,
  type StaffCommand,
} from '../../../shared/dining/local/staffClient';
import {
  Field,
  Pick,
  Text,
  Check,
  FormBox,
  useValues,
  integer,
  type FormContext,
} from './fields';
import styles from './local.module.css';

/** Owner sees only company-qualified records; no descriptive function grants authority. */
export function StaffForms({ context }: { context: FormContext }) {
  const { t } = useTranslation();
  const v = useValues({
    issuer: '',
    subject: '',
    code: '',
    name: '',
    member: '',
    functionCode: '',
    fr: '',
    en: '',
    ar: '',
    tasks: '',
    function: '',
    state: '',
    reason: '',
  });
  const [active, setActive] = useState(true);
  const members = (context.data.memberships ?? []).filter(
    (row) => row.role !== 'owner',
  );
  const people = members.map((row) => {
    const profile = context.data.staff_profiles?.find(
      (p) => p.membership_id === row.id,
    );
    return {
      value: String(row.id),
      label: `${profile?.display_name ?? '#' + row.id} · ${profile?.employee_code ?? ''} · ${t('d1.state_' + row.status)}`,
    };
  });
  const functions = (context.data.staff_functions ?? []).map((row) => ({
    value: String(row.id),
    label: localized(row.labels),
  }));
  const person = (name: string) => (
    <Pick
      name={name}
      label="person"
      value={v.get('member')}
      set={(value) => {
        v.set('member', value);
        const profile = context.data.staff_profiles?.find(
          (row) => String(row.membership_id) === value,
        );
        if (profile) {
          v.set('code', profile.employee_code);
          v.set('name', profile.display_name);
        }
      }}
      options={people}
    />
  );
  const field = (
    key: Parameters<typeof v.get>[0],
    label: string,
    type = 'text',
  ) => (
    <Field
      name={key}
      label={label}
      value={v.get(key)}
      set={(value) => v.set(key, value)}
      type={type}
    />
  );
  const save = (command: StaffCommand) =>
    submitStaff(context.api, context.scope, command);
  const selected = members.find((row) => String(row.id) === v.get('member'));
  return (
    <section aria-label={t('d1.section_staff')}>
      <header className={styles.sectionIntro}>
        <h2>{t('d1.section_staff')}</h2>
        <p>{t('d1.staffIdentityNotice')}</p>
        <p>{t('d1.staffNoImplicit')}</p>
      </header>
      <div
        className={styles.table}
        role="region"
        aria-label={t('d1.staffProfile')}
        tabIndex={0}
      >
        <table>
          <caption>{t('d1.staffProfile')}</caption>
          <thead>
            <tr>
              <th>{t('d1.person')}</th>
              <th>{t('d1.staffCode')}</th>
              <th>{t('d1.staffStatus')}</th>
              <th>{t('d1.staffAcceptance')}</th>
            </tr>
          </thead>
          <tbody>
            {(context.data.staff_profiles ?? []).map((row) => (
              <tr key={row.id}>
                <td>{row.display_name}</td>
                <td>{row.employee_code}</td>
                <td>
                  {t(
                    'd1.state_' +
                      (members.find((m) => m.id === row.membership_id)
                        ?.status ?? 'pending'),
                  )}
                </td>
                <td>
                  {t(
                    row.accepted_at
                      ? 'd1.staffAcceptedYes'
                      : 'd1.staffAcceptedNo',
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <FormBox
        context={context}
        title="staffInvite"
        operation="staff_invite"
        submit={() =>
          save({
            operation: 'invite',
            issuer: v.get('issuer'),
            subject: v.get('subject'),
            employee_code: v.get('code'),
            display_name: v.get('name'),
          })
        }
      >
        {field('issuer', 'staffIssuer')}
        {field('subject', 'staffSubject')}
        {field('code', 'staffCode')}
        {field('name', 'staffName')}
      </FormBox>
      <FormBox
        context={context}
        title="staffProfile"
        operation="staff_profile"
        submit={() =>
          save({
            operation: 'profile',
            membership_id: integer(v.get('member')),
            employee_code: v.get('code'),
            display_name: v.get('name'),
          })
        }
      >
        {person('profile_member')}
        {field('code', 'staffCode')}
        {field('name', 'staffName')}
      </FormBox>
      <FormBox
        context={context}
        title="staffFunctions"
        operation="staff_function"
        submit={() =>
          save({
            operation: 'function',
            code: v.get('functionCode'),
            labels: { fr: v.get('fr'), en: v.get('en'), ar: v.get('ar') },
            tasks: v
              .get('tasks')
              .split('\n')
              .map((value) => value.trim())
              .filter(Boolean),
            active,
          })
        }
      >
        <p>{t('d1.staffFunctionCodeHint')}</p>
        {field('functionCode', 'code')}
        {field('fr', 'fr')}
        {field('en', 'en')}
        {field('ar', 'ar')}
        <Text
          label="staffTasks"
          name="tasks"
          value={v.get('tasks')}
          set={(value) => v.set('tasks', value)}
          required={false}
        />
        <Check
          label="active"
          name="function_active"
          value={active}
          set={setActive}
        />
      </FormBox>
      <FormBox
        context={context}
        title="staffAssign"
        operation="staff_assignment"
        submit={() =>
          save({
            operation: 'assignment',
            membership_id: integer(v.get('member')),
            function_id: integer(v.get('function')),
            active,
          })
        }
      >
        {person('assignment_member')}
        <Pick
          label="staffFunction"
          name="function"
          value={v.get('function')}
          set={(value) => v.set('function', value)}
          options={functions}
        />
        <Check
          label="active"
          name="assignment_active"
          value={active}
          set={setActive}
        />
      </FormBox>
      <FormBox
        context={context}
        title="staffLifecycle"
        operation="staff_status"
        submitDisabled={!selected?.revision}
        submit={() =>
          save({
            operation: 'status',
            membership_id: integer(v.get('member')),
            expected_revision: selected!.revision!,
            status: v.get('state') as 'active' | 'suspended' | 'revoked',
            reason: v.get('reason'),
          })
        }
      >
        {person('status_member')}
        <Pick
          label="staffState"
          name="staff_state"
          value={v.get('state')}
          set={(value) => v.set('state', value)}
          options={['active', 'suspended', 'revoked'].map((value) => ({
            value,
            label: t('d1.state_' + value),
          }))}
        />
        <Text
          label="staffReason"
          name="reason"
          value={v.get('reason')}
          set={(value) => v.set('reason', value)}
        />
      </FormBox>
      <div className={styles.card}>
        <h3>{t('d1.staffFunctions')}</h3>
        {(context.data.staff_functions ?? []).map((row) => (
          <p key={row.id}>
            <strong>{localized(row.labels)}</strong> · {row.tasks.join(' · ')}
          </p>
        ))}
        <h3>{t('d1.staffAssign')}</h3>
        {(context.data.staff_assignments ?? []).map((row) => (
          <p key={row.id}>
            {people.find((p) => p.value === String(row.membership_id))?.label} ·{' '}
            {functions.find((f) => f.value === String(row.function_id))?.label}{' '}
            · {t(row.active ? 'd1.state_active' : 'd1.state_revoked')}
          </p>
        ))}
      </div>
    </section>
  );
}

/** Pending relationships are accessible only through the signed personal discovery route. */
export function PersonalInvitations({ api }: { api: LocalDiningClient }) {
  const { t } = useTranslation();
  const [rows, setRows] = useState<StaffInvitation[]>([]),
    [busy, setBusy] = useState(true),
    [error, setError] = useState(false),
    [saved, setSaved] = useState(false);
  useEffect(() => {
    let current = true;
    void ownInvitations(api)
      .then((value) => {
        if (current) setRows(value);
      })
      .catch(() => {
        if (current) setError(true);
      })
      .finally(() => {
        if (current) setBusy(false);
      });
    return () => {
      current = false;
    };
  }, [api]);
  const refresh = async () => {
    setBusy(true);
    setError(false);
    try {
      setRows(await ownInvitations(api));
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  };
  return (
    <details className={styles.card}>
      <summary>{t('d1.staffInvitations')}</summary>
      {error && <p role="alert">{t('d1.staffError')}</p>}
      {saved && <p role="status">{t('d1.staffAccepted')}</p>}
      {busy && <p role="status">{t('common.loading')}</p>}
      {!rows.length && !error && !busy && <p>{t('d1.staffNone')}</p>}
      {rows.map((row) => (
        <div key={`${row.membership_id}:${row.branch_id}`}>
          <p>
            {row.organization_name} · {row.display_name} · {row.employee_code}
          </p>
          <Button
            type="button"
            disabled={busy || row.accepted}
            onClick={() => {
              setBusy(true);
              setError(false);
              void acceptEmployment(api, row)
                .then(async () => {
                  setSaved(true);
                  setRows(await ownInvitations(api));
                })
                .catch(() => setError(true))
                .finally(() => setBusy(false));
            }}
          >
            {t('d1.staffAccept')}
          </Button>
        </div>
      ))}
      <Button
        type="button"
        variant="secondary"
        disabled={busy}
        onClick={() => void refresh()}
      >
        {t('d1.staffRefresh')}
      </Button>
    </details>
  );
}
