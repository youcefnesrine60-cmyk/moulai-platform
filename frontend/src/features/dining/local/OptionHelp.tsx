// MoulAI™ — choice explanations stay outside native option elements.
import { useTranslation } from 'react-i18next';
import { optionExplanation } from '../../../shared/dining/help/optionHelp';
import styles from './assistance.module.css';
export function OptionHelp({
  name,
  label,
  value,
  options,
  id,
}: {
  name: string;
  label: string;
  value: string;
  options: readonly { value: string; label: string }[];
  id: string;
}) {
  const { t, i18n } = useTranslation();
  const locale =
    i18n.language === 'ar' ? 'ar' : i18n.language === 'en' ? 'en' : 'fr';
  const explain = (choice: string) =>
    label === 'testProfile'
      ? t('options.profile_' + choice)
      : (optionExplanation(name, label, choice, locale) ??
        t('options.unverified'));
  const summary = value
    ? (explain(value).match(/^.*?[.!؟](?:\s|$)/u)?.[0] ?? explain(value))
    : '';
  return (
    <div className={styles.optionHelp}>
      <p id={id}>
        {value ? (
          <>
            <strong>
              {t('options.selected')}:{' '}
              <bdi>{options.find((row) => row.value === value)?.label}</bdi>
            </strong>{' '}
            — {summary}
          </>
        ) : (
          t('options.none')
        )}
      </p>
      <details>
        <summary>{t('options.details')}</summary>
        <p>
          {t(label === 'testProfile' ? 'options.profileRule' : 'options.rules')}
        </p>
        <dl>
          {options.map((row) => (
            <div key={row.value}>
              <dt>
                <bdi>{row.label}</bdi>
              </dt>
              <dd>{explain(row.value)}</dd>
            </div>
          ))}
        </dl>
      </details>
    </div>
  );
}
