// MoulAI™ — nearby help is independent of disabled business controls and never submits a form.
import { useTranslation } from 'react-i18next';
import { requestDiningHelp } from '../../../shared/dining/help/requests';
import styles from './assistance.module.css';
export function ElementHelp({
  targetId,
  labelKey,
}: {
  targetId: string;
  labelKey: string;
}) {
  const { t } = useTranslation();
  return (
    <a
      role="button"
      href="#dining-element-help"
      aria-haspopup="dialog"
      className={styles.elementHelp}
      aria-label={t('element.explainNamed', { name: t('d1.' + labelKey) })}
      title={t('help.fieldHelp')}
      onClick={(event) => {
        event.preventDefault();
        requestDiningHelp({ mode: 'guide', field: true, elementId: targetId });
      }}
      onKeyDown={(event) => {
        if (event.key === ' ') {
          event.preventDefault();
          event.currentTarget.click();
        }
      }}
    >
      <span aria-hidden="true">?</span>
    </a>
  );
}
