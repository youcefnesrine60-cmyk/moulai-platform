// MoulAI™ — distinguish civil dates, legacy wall-clock observations and exact instants.
import { PresentationDataError } from '../ui/RenderRecovery';
export function isWallClock(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    /^(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$/.test(value)
  );
}
export function checkedDay(value: string): Date {
  const date = new Date(value + 'T12:00:00Z');
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(value) ||
    !Number.isFinite(date.getTime()) ||
    date.toISOString().slice(0, 10) !== value
  )
    throw new PresentationDataError('invalid_planning_day');
  return date;
}
export function checkedInstant(value: string): Date {
  if (
    typeof value !== 'string' ||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$/.test(
      value,
    )
  )
    throw new PresentationDataError('invalid_instant');
  checkedDay(value.slice(0, 10));
  const date = new Date(value);
  if (!Number.isFinite(date.getTime()))
    throw new PresentationDataError('invalid_instant');
  return date;
}
export function checkedTimezone(timezone: string): string {
  if (typeof timezone !== 'string' || !timezone)
    throw new PresentationDataError('invalid_timezone');
  try {
    new Intl.DateTimeFormat('en', { timeZone: timezone }).resolvedOptions();
    return timezone;
  } catch {
    throw new PresentationDataError('invalid_timezone');
  }
}
