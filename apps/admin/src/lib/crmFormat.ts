export function money(cents: number | null | undefined, currency = "CAD"): string {
  return moneyExact(cents, currency);
}

export function moneyExact(cents: number | null | undefined, currency = "CAD"): string {
  if (cents === null || cents === undefined) return "—";
  return new Intl.NumberFormat("en-CA", { style: "currency", currency }).format(cents / 100);
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-CA", { dateStyle: "medium" }).format(new Date(iso));
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-CA", { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(iso)
  );
}

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return shortDate(iso);
}

export function titleCase(value: string | null | undefined): string {
  if (!value) return "—";
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function initials(name: string | null | undefined): string {
  if (!name) return "?";
  return name
    .split(" ")
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

type Tone = "blue" | "green" | "red" | "amber" | "violet" | "slate" | "teal" | "sky";

export const STATUS_TONE: Record<string, Tone> = {
  // leads
  new: "sky",
  contacted: "blue",
  qualified: "violet",
  unqualified: "slate",
  nurturing: "amber",
  converted: "green",
  // companies
  lead: "slate",
  prospect: "sky",
  negotiating: "amber",
  active_merchant: "green",
  churned: "red",
  // deals
  prospecting: "slate",
  meeting_scheduled: "violet",
  quote_sent: "violet",
  negotiation: "amber",
  contract_review: "teal",
  won: "green",
  lost: "red",
  hold: "slate",
  // quotations / contracts
  draft: "slate",
  sent: "blue",
  approved: "green",
  rejected: "red",
  expired: "red",
  pending_signature: "amber",
  active: "green",
  renewed: "teal",
  terminated: "red",
  // tasks
  open: "blue",
  in_progress: "amber",
  done: "green",
  cancelled: "slate",
  // priority
  low: "slate",
  medium: "sky",
  high: "amber",
  urgent: "red",
};

// ---- CSV helpers (client-side parse / generate) ----
export function parseCsv(text: string): Array<Record<string, string>> {
  const rows: string[][] = [];
  let field = "";
  let row: string[] = [];
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (inQuotes) {
      if (char === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += char;
      }
    } else if (char === '"') {
      inQuotes = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n" || char === "\r") {
      if (char === "\r" && text[i + 1] === "\n") i++;
      row.push(field);
      field = "";
      if (row.some((c) => c.trim() !== "")) rows.push(row);
      row = [];
    } else {
      field += char;
    }
  }
  if (field !== "" || row.length) {
    row.push(field);
    if (row.some((c) => c.trim() !== "")) rows.push(row);
  }
  if (rows.length === 0) return [];
  const header = rows[0].map((h) => h.trim());
  return rows.slice(1).map((cells) => {
    const obj: Record<string, string> = {};
    header.forEach((key, idx) => {
      obj[key] = (cells[idx] ?? "").trim();
    });
    return obj;
  });
}

export function toCsv(headers: string[], rows: string[][]): string {
  const escape = (value: string) =>
    /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
  return [headers, ...rows].map((r) => r.map(escape).join(",")).join("\n");
}

export function downloadCsv(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
