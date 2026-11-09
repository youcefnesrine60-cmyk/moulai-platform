import { useTranslation } from 'react-i18next';
import { Button } from '../../../shared/ui/primitives';
import { requestDiningHelp } from '../../../shared/dining/help/requests';
export function HelpLink({
  operation,
  resolve = false,
}: {
  operation?: string;
  resolve?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <Button
      type="button"
      variant="secondary"
      onClick={() =>
        requestDiningHelp({
          mode: 'guide',
          ...(operation ? { operation } : {}),
        })
      }
    >
      {t(resolve ? 'help.resolve' : 'help.context')}
    </Button>
  );
}
