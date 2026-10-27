// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useState, type ReactElement } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import * as Select from '@radix-ui/react-select';
import {
  ArrowUpRight,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  Clock3,
  LockKeyhole,
  MessagesSquare,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import { Navigate, useNavigate } from 'react-router';
import { useAdapter, useSession } from '../../app/access';
import {
  Brand,
  Button,
  ForwardArrow,
  AppearanceControls,
  LoadingPanel,
} from '../../shared/ui/primitives';
import styles from './access.module.css';

const profiles = [
  'owner',
  'manager',
  'employee',
  'empty',
  'admin',
  'unlinked',
  'suspended',
  'error',
] as const;
const profileSchema = z.object({ profile: z.enum(profiles) });
type ProfileForm = z.infer<typeof profileSchema>;

/** An explicit local review entry, never an alternative to trusted authentication. */
function ReviewForm(): ReactElement {
  const { t } = useTranslation();
  const adapter = useAdapter();
  const client = useQueryClient();
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);
  const {
    control,
    handleSubmit,
    formState: { isSubmitting, errors },
  } = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: { profile: 'owner' },
  });

  /** Replace all prior review data before establishing the next ephemeral profile. */
  const open = async ({ profile }: ProfileForm): Promise<void> => {
    setFailed(false);
    try {
      await client.cancelQueries();
      await adapter.openReview(profile);
      client.clear();
      navigate(profile === 'admin' ? '/platform' : '/workspace', {
        replace: true,
      });
    } catch {
      setFailed(true);
    }
  };

  return (
    <form
      onSubmit={(event) => void handleSubmit(open)(event)}
      className={styles.reviewForm}
    >
      <h2>{t('review.title')}</h2>
      <p id="review-help">{t('review.help')}</p>
      <label htmlFor="review-profile">{t('review.profile')}</label>
      <Controller
        name="profile"
        control={control}
        render={({ field }) => (
          <Select.Root
            value={field.value}
            onValueChange={field.onChange}
            disabled={isSubmitting}
          >
            <Select.Trigger
              id="review-profile"
              ref={field.ref}
              className={styles.selectTrigger}
              aria-describedby="review-help"
              aria-invalid={Boolean(errors.profile)}
            >
              <Select.Value />
              <Select.Icon>
                <ChevronDown size={17} aria-hidden="true" />
              </Select.Icon>
            </Select.Trigger>
            <Select.Portal>
              <Select.Content
                className={styles.selectContent}
                position="popper"
                sideOffset={6}
              >
                <Select.Viewport>
                  {profiles.map((profile) => (
                    <Select.Item
                      className={styles.selectItem}
                      key={profile}
                      value={profile}
                    >
                      <Select.ItemText>
                        {t(`profile.${profile}`)}
                      </Select.ItemText>
                      <Select.ItemIndicator>
                        <Check size={15} />
                      </Select.ItemIndicator>
                    </Select.Item>
                  ))}
                </Select.Viewport>
              </Select.Content>
            </Select.Portal>
          </Select.Root>
        )}
      />
      {errors.profile && <p role="alert">{t('review.invalid')}</p>}
      {failed && <p role="alert">{t('state.temporary.body')}</p>}
      <Button type="submit" disabled={isSubmitting}>
        {t('review.open')}
        <ForwardArrow />
      </Button>
    </form>
  );
}

/** No credential fields and no remote login call until Business Integration. */
export function AccessPage(): ReactElement {
  const { t } = useTranslation();
  const adapter = useAdapter();
  const session = useSession();
  if (session.isPending) return <LoadingPanel />;
  if (session.data)
    return (
      <Navigate
        to={session.data.area === 'platform' ? '/platform' : '/workspace'}
        replace
      />
    );
  return (
    <div className={styles.page}>
      {adapter.mode === 'synthetic' && (
        <div className={styles.reviewBanner}>{t('review.banner')}</div>
      )}
      <header className={styles.header}>
        <Brand prominent />
        <AppearanceControls />
      </header>
      <main className={styles.main}>
        <aside className={styles.editorial}>
          <div className={styles.editorialCopy}>
            <span className={styles.editorialKicker}>
              <bdi>MoulAI™</bdi> / {t('nav.context')}
            </span>
            <h2>{t('access.editorialTitle')}</h2>
            <p>{t('access.editorialBody')}</p>
            <div className={styles.editorialFeatures}>
              {['One', 'Two', 'Three'].map((key) => (
                <p key={key}>
                  <CheckCircle2 size={18} aria-hidden="true" />
                  {t(`access.feature${key}`)}
                </p>
              ))}
            </div>
            <small>{t('access.editorialFooter')}</small>
          </div>
        </aside>
        <section className={styles.entry}>
          <p className="eyebrow">{t('access.eyebrow')}</p>
          <h1>{t('access.title')}</h1>
          <p className={styles.description}>{t('access.description')}</p>
          <Button disabled aria-describedby="connection-status">
            {t('access.signin')}
            <ArrowUpRight size={18} aria-hidden="true" />
          </Button>
          <p id="connection-status" className={styles.connectionStatus}>
            <LockKeyhole size={16} aria-hidden="true" />
            {t('access.unavailable')}
          </p>
          {adapter.mode === 'synthetic' && <ReviewForm />}
          <p className={styles.privacy}>
            <LockKeyhole size={14} aria-hidden="true" />
            {t('access.privacy')}
          </p>
        </section>
        <section
          className={styles.servicePresentation}
          aria-labelledby="service-title"
          aria-describedby="service-vision"
        >
          <div className={styles.serviceHeading}>
            <h2 id="service-title" dir="ltr">
              {t('access.serviceTitle')}
            </h2>
            <p className={styles.serviceLead}>{t('access.serviceLead')}</p>
          </div>
          <div className={styles.serviceCopy}>
            <p>{t('access.serviceTeam')}</p>
          </div>
          <ul className={styles.serviceCapabilities}>
            {(
              [
                ['access.serviceCustomers', MessagesSquare],
                ['access.serviceAppointments', CalendarDays],
                ['access.serviceOrders', ClipboardList],
                ['access.serviceContinuous', Clock3],
              ] as const
            ).map(([key, Icon]) => (
              <li key={key}>
                <Icon size={28} aria-hidden="true" />
                <span>{t(key)}</span>
              </li>
            ))}
          </ul>
          <p id="service-vision" className={styles.serviceVision}>
            {t('access.serviceVision')}
          </p>
        </section>
      </main>
      <footer className={styles.footer}>
        <span dir="ltr">© 2026 MoulAI™</span>
      </footer>
    </div>
  );
}
