/**
 * Format a timestamp in Indian Standard Time (Asia/Kolkata).
 *
 * The backend stores naive UTC datetimes (Python `datetime.utcnow`), so a
 * string without a timezone suffix is treated as UTC and converted to IST.
 * Strings that already carry an offset (Z or +hh:mm) are used as-is.
 */
export function formatIST(dateString: string | null | undefined): string {
  if (!dateString) return '-';

  const hasZone = /Z$|[+-]\d{2}:\d{2}$/.test(dateString);
  const iso = hasZone ? dateString : `${dateString.replace(/Z$/, '')}Z`;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '-';

  return date.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  }) + ' IST';
}

/** Compact IST timestamp for chat bubbles: 03 Oct 2026, 8:45 PM IST */
export function formatISTShort(dateString: string | null | undefined): string {
  if (!dateString) return '';
  const hasZone = /Z$|[+-]\d{2}:\d{2}$/.test(dateString);
  const iso = hasZone ? dateString : `${dateString.replace(/Z$/, '')}Z`;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';

  return date.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  }) + ' IST';
}
