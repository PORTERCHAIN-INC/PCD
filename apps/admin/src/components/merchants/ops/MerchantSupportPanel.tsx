"use client";

import Link from "next/link";
import { LifeBuoy } from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { merchantOps } from "@/lib/merchant-ops";
import { relativeTime, titleCase } from "@/lib/crmFormat";
import { Empty, Panel, Pill, SkeletonRows } from "./ui";

const OPEN = new Set(["open", "pending", "in_progress", "new", "investigating"]);

/** Tickets, claims and delivery exceptions for this merchant, open first, then newest. */
export function MerchantSupportPanel({ id }: { id: string }) {
  const { data, error } = useApiData((t) => merchantOps.support(t, id), [id], {
    key: `merchant-support-${id}`,
  });
  const rows = [
    ...(data?.tickets ?? []).map((r) => ({
      key: `t-${r.id}`,
      kind: "Ticket",
      title: r.subject,
      status: r.status,
      at: r.created_at,
      href: `/support/${r.id}`,
    })),
    ...(data?.claims ?? []).map((r) => ({
      key: `c-${r.id}`,
      kind: "Claim",
      title: titleCase(r.type),
      status: r.status,
      at: r.created_at,
      href: `/claims/${r.id}`,
    })),
    ...(data?.exceptions ?? []).map((r) => ({
      key: `e-${r.id}`,
      kind: "Exception",
      title: [titleCase(r.type), r.tracking_number].filter(Boolean).join(" · "),
      status: r.status,
      at: r.created_at,
      href: `/orders/${r.order_id}`,
    })),
  ].sort(
    (a, b) =>
      Number(OPEN.has(b.status)) - Number(OPEN.has(a.status)) ||
      String(b.at).localeCompare(String(a.at))
  );
  const open = rows.filter((r) => OPEN.has(r.status)).length;
  return (
    <Panel
      title="Tickets, claims & exceptions"
      aside={
        <Link
          href={`/support?merchant_id=${id}`}
          className="inline-flex min-h-11 items-center rounded-full px-3 text-sm font-semibold text-secondary hover:bg-secondary/5"
        >
          Open in Support
        </Link>
      }
    >
      {!data && !error ? (
        <SkeletonRows rows={3} label="Loading support" />
      ) : error ? (
        <Empty title="Couldn't load support" hint={error} />
      ) : rows.length === 0 ? (
        <Empty
          icon={<LifeBuoy className="h-6 w-6" aria-hidden />}
          title="All quiet"
          hint="No tickets, claims or delivery exceptions for this merchant."
        />
      ) : (
        <>
          <p className="text-2xl font-extrabold tracking-tight text-primary tabular-nums">
            {open} open{" "}
            <span className="text-base font-semibold text-slate-600">of {rows.length}</span>
          </p>
          <ul className="mt-4 divide-y divide-primary/5 border-t border-primary/5">
            {rows.map((r) => (
              <li key={r.key}>
                <Link
                  href={r.href}
                  className="flex min-h-12 items-center gap-3 rounded-xl py-2.5 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-secondary"
                >
                  <span className="w-20 shrink-0 text-[11px] font-semibold tracking-[0.14em] text-slate-600 uppercase">
                    {r.kind}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm font-medium text-primary">
                    {r.title}
                  </span>
                  {OPEN.has(r.status) ? (
                    <Pill tone="amber">{titleCase(r.status)}</Pill>
                  ) : (
                    <span className="text-xs text-slate-600">{titleCase(r.status)}</span>
                  )}
                  <span className="hidden w-20 shrink-0 text-right text-xs text-slate-600 sm:block">
                    {relativeTime(r.at)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </Panel>
  );
}
