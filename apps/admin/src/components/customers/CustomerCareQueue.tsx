"use client";

import Link from "next/link";
import { useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { Badge, Button, SectionCard } from "@/components/crm/primitives";
import { customer360Api } from "@/lib/customers";

/** Two human gates that rules feed: deletion approvals and reorder-nudge approvals. */
export default function CustomerCareQueue({ canWrite }: { canWrite: boolean }) {
  const { getApiToken } = useAdminAuth();
  const [v, setV] = useState(0);
  const [msg, setMsg] = useState<string | null>(null);
  const { data: jobs } = useApiData((t) => customer360Api.privacyJobs(t, "pending_review"), [v], { key: `care-jobs-${v}` });
  const { data: nudges } = useApiData((t) => customer360Api.nudges(t), [v], { key: `care-nudges-${v}` });

  async function act(fn: (t: string) => Promise<string>) {
    try {
      setMsg(await fn(await getApiToken()));
      setV((x) => x + 1);
    } catch (e) {
      setMsg((e as Error).message);
    }
  }

  const drafts = nudges?.nudges ?? [];
  return (
    <div className="grid gap-4 lg:grid-cols-2" data-testid="customer-care-queue">
      <SectionCard title={`Deletion requests · ${jobs?.length ?? 0} to review`}>
        <ul className="divide-y divide-primary/5">
          {(jobs ?? []).slice(0, 5).map((j) => (
            <li key={j.id} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
              <span className="font-semibold text-primary">{j.reference}</span>
              <span className="flex items-center gap-2">
                {j.plan.blockers?.active_deliveries?.length ? <Badge tone="amber">Waiting on delivery</Badge> : <Badge tone="green">Ready</Badge>}
                {j.customer_id ? (
                  <Link href={`/customers/${j.customer_id}`} className="font-semibold text-primary underline underline-offset-4">
                    Review
                  </Link>
                ) : null}
              </span>
            </li>
          ))}
          {jobs && jobs.length === 0 ? <li className="px-5 py-3 text-sm text-primary/70">Nothing to review.</li> : null}
        </ul>
      </SectionCard>
      <SectionCard title={`Reorder nudges · ${drafts.length} drafted`}>
        <div className="space-y-3 p-5 text-sm">
          <p className="text-primary/75">
            {nudges?.enabled ? "Sending is on. Each batch still needs your approval." : "Sending is off (Settings → Customers → reorder_nudges_enabled). Drafts only."}
          </p>
          <ul className="space-y-1">
            {drafts.slice(0, 5).map((n) => (
              <li key={n.id} className="flex justify-between gap-3">
                <span className="truncate font-semibold text-primary">{n.name || n.email}</span>
                <span className="shrink-0 text-xs text-primary/65">{n.reason}</span>
              </li>
            ))}
          </ul>
          {canWrite ? (
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => void act(async (t) => `Drafted ${(await customer360Api.draftNudges(t)).drafted}.`)}>
                Find due customers
              </Button>
              <Button
                disabled={!drafts.length || !nudges?.enabled}
                onClick={() => void act(async (t) => `Approved ${(await customer360Api.decideNudges(t, drafts.map((d) => d.id), true)).decided}.`)}
              >
                Approve & send {drafts.length || ""}
              </Button>
              <Button
                variant="outline"
                disabled={!drafts.length}
                onClick={() => void act(async (t) => `Skipped ${(await customer360Api.decideNudges(t, drafts.map((d) => d.id), false)).decided}.`)}
              >
                Skip all
              </Button>
            </div>
          ) : null}
          {msg ? <p role="status" className="font-medium text-primary">{msg}</p> : null}
        </div>
      </SectionCard>
    </div>
  );
}
