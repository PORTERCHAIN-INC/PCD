/**
 * Next quote-response deadline for SLA countdown (Mon–Fri, 5 PM America/Toronto).
 * Matches marketing copy: "Response within one business day."
 */

const RESPONSE_HOUR = 17;
const RESPONSE_MINUTE = 0;

function isWeekday(date: Date): boolean {
  const day = date.getDay();
  return day >= 1 && day <= 5;
}

function atResponseTime(date: Date): Date {
  const d = new Date(date);
  d.setHours(RESPONSE_HOUR, RESPONSE_MINUTE, 0, 0);
  return d;
}

/** Returns the next 5 PM ET on a weekday when quote responses are due. */
export function getNextQuoteResponseDeadline(now: Date = new Date()): Date {
  const candidate = atResponseTime(now);
  if (isWeekday(now) && now < candidate) {
    return candidate;
  }
  const next = new Date(now);
  next.setDate(next.getDate() + 1);
  while (!isWeekday(next)) {
    next.setDate(next.getDate() + 1);
  }
  return atResponseTime(next);
}

export function formatQuoteResponseDeadline(deadline: Date, locale: string): string {
  return new Intl.DateTimeFormat(locale === "fr" ? "fr-CA" : "en-CA", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/Toronto",
    timeZoneName: "short",
  }).format(deadline);
}
