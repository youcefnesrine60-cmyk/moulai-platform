// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import { useEffect, useRef, useState, type ReactElement } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
import { useAdapter } from '../../app/access';
import { ReviewConflict } from '../../shared/business/contracts';
import {
  agentTones,
  type AgentDraft,
  type AgentView,
} from '../../shared/intelligence/contracts';
import { agentDraftSchema } from '../../shared/intelligence/validation';
import { AppearanceControls, Button } from '../../shared/ui/primitives';
import { useIntelligence } from './scope';
import shared from '../management/management.module.css';
import styles from './intelligence.module.css';

/** Two-step local descriptive edit; no activation, provider config or remote operation. */
export function AgentEditor({
  agent,
  revision,
  close,
}: {
  agent: AgentView;
  revision: number;
  close: () => void;
}): ReactElement {
  const { t } = useTranslation();
  const adapter = useAdapter();
  const context = useIntelligence();
  const client = useQueryClient();
  const controller = useRef<AbortController | null>(null);
  const opener = useRef(
    document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null,
  );
  const [draft, setDraft] = useState<AgentDraft | null>(null);
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState<'stale' | 'failed' | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AgentDraft>({
    resolver: zodResolver(agentDraftSchema),
    defaultValues: {
      name: agent.name,
      description: agent.description,
      language: agent.language,
      tone: agent.tone,
    },
  });
  useEffect(() => () => controller.current?.abort(), []);
  /** Keep the operation bound to its original scope and cancel it when the dialog exits. */
  const save = async (): Promise<void> => {
    if (!draft || pending) return;
    controller.current = new AbortController();
    const signal = controller.current.signal;
    setPending(true);
    setFailure(null);
    try {
      await adapter.saveAgentReview(
        context.scope,
        agent.id,
        revision,
        draft,
        signal,
      );
      if (signal.aborted) return;
      await client.invalidateQueries({
        queryKey: [...context.intelligenceKey, 'agents'],
      });
      close();
    } catch (error) {
      if (!signal.aborted)
        setFailure(error instanceof ReviewConflict ? 'stale' : 'failed');
    } finally {
      if (!signal.aborted) setPending(false);
    }
  };
  return (
    <Dialog.Root
      open
      onOpenChange={(open) => {
        if (!open) close();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className={shared.overlay} />
        <Dialog.Content
          className={shared.dialog}
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            if (opener.current?.isConnected) opener.current.focus();
          }}
        >
          <Dialog.Title>{t('intelligence.configure')}</Dialog.Title>
          <Dialog.Description>
            {t('intelligence.editNotice')}
          </Dialog.Description>
          <AppearanceControls />
          <Dialog.Close
            className={styles.close}
            aria-label={t('intelligence.closeEditor')}
          >
            <X size={20} aria-hidden="true" />
          </Dialog.Close>
          {draft ? (
            <>
              <h2>{t('intelligence.confirmTitle')}</h2>
              <dl className={styles.facts}>
                <div>
                  <dt>{t('intelligence.name')}</dt>
                  <dd dir="auto">{draft.name}</dd>
                </div>
                <div>
                  <dt>{t('intelligence.description')}</dt>
                  <dd dir="auto">
                    {draft.description || t('intelligence.notProvided')}
                  </dd>
                </div>
                <div>
                  <dt>{t('intelligence.language')}</dt>
                  <dd>{draft.language.toUpperCase()}</dd>
                </div>
                <div>
                  <dt>{t('intelligence.tone')}</dt>
                  <dd>{t(`intelligence.tone.${draft.tone}`)}</dd>
                </div>
              </dl>
              <div className={shared.actions}>
                <Button
                  variant="secondary"
                  disabled={pending}
                  onClick={() => setDraft(null)}
                >
                  {t('intelligence.backEdit')}
                </Button>
                <Button disabled={pending} onClick={() => void save()}>
                  {t('intelligence.applyReview')}
                </Button>
              </div>
            </>
          ) : (
            <form
              className={shared.form}
              noValidate
              onSubmit={(event) =>
                void handleSubmit((value) => setDraft(value))(event)
              }
            >
              {(['name', 'description', 'language', 'tone'] as const).map(
                (field) => (
                  <label key={field} className={shared.field}>
                    <span id={`agent-${field}-label`}>
                      {t(`intelligence.${field}`)}
                    </span>
                    {field === 'name' ? (
                      <input
                        {...register(field)}
                        maxLength={100}
                        aria-labelledby={`agent-${field}-label`}
                        aria-invalid={Boolean(errors[field])}
                        aria-describedby={
                          errors[field] ? `agent-${field}-error` : undefined
                        }
                      />
                    ) : field === 'description' ? (
                      <textarea
                        {...register(field)}
                        maxLength={500}
                        aria-labelledby={`agent-${field}-label`}
                        aria-invalid={Boolean(errors[field])}
                        aria-describedby={
                          errors[field] ? `agent-${field}-error` : undefined
                        }
                      />
                    ) : (
                      <select
                        {...register(field)}
                        aria-labelledby={`agent-${field}-label`}
                        aria-invalid={Boolean(errors[field])}
                      >
                        {(field === 'language'
                          ? ['fr', 'en', 'ar']
                          : agentTones
                        ).map((value) => (
                          <option key={value} value={value}>
                            {field === 'language'
                              ? value.toUpperCase()
                              : t(`intelligence.tone.${value}`)}
                          </option>
                        ))}
                      </select>
                    )}
                    {errors[field] && (
                      <span
                        id={`agent-${field}-error`}
                        className={shared.fieldError}
                      >
                        {t('intelligence.invalid')}
                      </span>
                    )}
                  </label>
                ),
              )}
              <Button type="submit">{t('intelligence.preview')}</Button>
            </form>
          )}
          {failure && <p role="alert">{t(`intelligence.${failure}`)}</p>}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
