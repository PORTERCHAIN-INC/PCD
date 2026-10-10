/** Merchant detail: five tabs, panels inside them, and old ?tab= links mapped forward. */

export const TAB_IDS = new Set<string>(["overview", "orders", "money", "connections", "people"]);

/** Five tabs. Everything else is a panel inside one of them. */
export type TabId = "overview" | "orders" | "money" | "connections" | "people";
export type MoneyPanel =
  "pricing" | "quote" | "credit" | "invoices" | "contracts" | "statement" | "credits";
export type PeoplePanel =
  "team" | "contacts" | "locations" | "documents" | "support" | "activity" | "settings" | "privacy";
export type ActivityPanel = "timeline" | "activities" | "tasks";

export const MONEY_PANELS: { id: MoneyPanel; label: string }[] = [
  { id: "pricing", label: "Pricing" },
  { id: "quote", label: "Quote preview" },
  { id: "credit", label: "Credit" },
  { id: "invoices", label: "Invoices" },
  { id: "contracts", label: "Contracts" },
  { id: "statement", label: "Statement" },
  { id: "credits", label: "Credit notes" },
];

export const PEOPLE_PANELS: { id: PeoplePanel; label: string }[] = [
  { id: "team", label: "Team" },
  { id: "contacts", label: "Contacts" },
  { id: "locations", label: "Locations" },
  { id: "documents", label: "Documents" },
  { id: "support", label: "Tickets & claims" },
  { id: "activity", label: "Notes & tasks" },
  { id: "settings", label: "Account settings" },
  { id: "privacy", label: "Privacy" },
];

export const ACTIVITY_PANELS: { id: ActivityPanel; label: string }[] = [
  { id: "timeline", label: "Timeline" },
  { id: "activities", label: "CRM notes" },
  { id: "tasks", label: "Tasks" },
];

export const MONEY_IDS = new Set<string>(MONEY_PANELS.map((p) => p.id));
export const PEOPLE_IDS = new Set<string>(PEOPLE_PANELS.map((p) => p.id));
export const ACTIVITY_IDS = new Set<string>(ACTIVITY_PANELS.map((p) => p.id));

export type Route = { tab: TabId; money: MoneyPanel; people: PeoplePanel; activity: ActivityPanel };
const DEFAULT_ROUTE: Route = {
  tab: "overview",
  money: "pricing",
  people: "team",
  activity: "timeline",
};

/** Old links (?tab=pricing|api|settings|invoices|team|tasks…) keep working. */
export function parseMerchantTab(raw: string | null, panel: string | null = null): Route {
  const r = { ...DEFAULT_ROUTE };
  const key = raw ?? "";
  if (key === "api" || key === "integrations") return { ...r, tab: "connections" };
  if (key === "pricing" || MONEY_IDS.has(key))
    return { ...r, tab: "money", money: key as MoneyPanel };
  if (key === "settings") return { ...r, tab: "people", people: "settings" };
  if (PEOPLE_IDS.has(key)) return { ...r, tab: "people", people: key as PeoplePanel };
  if (ACTIVITY_IDS.has(key))
    return { ...r, tab: "people", people: "activity", activity: key as ActivityPanel };
  if (key === "analytics") return r;
  if (TAB_IDS.has(key)) {
    const tab = key as TabId;
    if (tab === "money" && panel && MONEY_IDS.has(panel))
      return { ...r, tab, money: panel as MoneyPanel };
    if (tab === "people" && panel) {
      if (PEOPLE_IDS.has(panel)) return { ...r, tab, people: panel as PeoplePanel };
      if (ACTIVITY_IDS.has(panel))
        return { ...r, tab, people: "activity", activity: panel as ActivityPanel };
    }
    return { ...r, tab };
  }
  return r;
}
