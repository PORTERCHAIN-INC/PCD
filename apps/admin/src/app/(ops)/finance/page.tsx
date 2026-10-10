import { redirect } from "next/navigation";

/** Old /finance?tab=… links land on the new Finance pages. */
const TAB_TO_PAGE: Record<string, string> = {
  overview: "/finance/cash",
  collections: "/finance/cash",
  interac: "/finance/cash",
  "merchant-ar": "/finance/invoices",
  invoices: "/finance/invoices",
  payments: "/finance/payments",
  payouts: "/finance/driver-pay",
  ledger: "/finance/reports",
  reports: "/finance/reports",
};

export default async function FinanceIndex({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const tab = (await searchParams).tab;
  redirect(TAB_TO_PAGE[typeof tab === "string" ? tab : ""] ?? "/finance/cash");
}
