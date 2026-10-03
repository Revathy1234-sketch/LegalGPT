export function formatIST(dateString: string | null | undefined): string {
  if (!dateString) return '-';
  
  // If the string already has timezone info, use it. Otherwise, treat it as local time.
  const isUtc = dateString.endsWith('Z');
  // If it's a naive string from Python (no Z), JS parses it as local time if we replace T with space or just parse it directly.
  const date = new Date(dateString.replace('Z', '')); 
  
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
