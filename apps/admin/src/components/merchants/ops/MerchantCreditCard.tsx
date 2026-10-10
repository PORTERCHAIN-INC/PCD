"use client";

import { useState } from "react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { merchantOps, cad, type MerchantOps } from "@/lib/merchant-ops";
import {
  ActionMenu,
  Dialog,
  FieldLabel,
  Panel,
  PrimaryAction,
  QuietButton,
  ReasonDialog,
  inputClass,
} from "./ui";

type Act = "hold" | "release" | "override" | "clear_override";
const COPY: Record<Act, { title: string; body: string; cta: string; danger?: boolean }> = {
  hold: {
    title: "Put on credit hold",
    body: "New bookings stop until you release the hold.",
    cta: "Put on hold",
    danger: true,
  },
  release: {
    title: "Release credit hold",
    body: "Bookings resume now. An overdue invoice can bring the hold back.",
    cta: "Release hold",
  },
  override: {
    title: "Allow bookings for 48 hours",
    body: "Use when the Interac e-Transfer is on its way.",
    cta: "Allow 48 h",
  },
  clear_override: {
    title: "End the override",
    body: "The hold applies again right away if anything is overdue.",
    cta: "End override",
  },
};

/** Credit: numbers, one sentence of state, one primary action. Interac e-Transfer only. */
export function MerchantCreditCard({ ops, onSaved }: { ops: MerchantOps; onSaved: () => void }) {
  const { getApiToken } = useAdminAuth();
  const c = ops.credit;
  const held = c.mode !== "none";
  const [act, setAct] = useState<Act | null>(null);
  const [limitOpen, setLimitOpen] = useState(false);
  const [limit, setLimit] = useState(c.limit_cents != null ? String(c.limit_cents / 100) : "");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);
  const limitValue = limit.trim() === "" ? null : Number(limit);
  const limitInvalid = limitValue != null && (!Number.isFinite(limitValue) || limitValue < 0);

  async function run(action: string, extra: Record<string, unknown> = {}, reason?: string) {
    setBusy(true);
    setMsg(null);
    try {
      const t = await getApiToken();
      await merchantOps.credit(t, ops.merchant_id, { action, reason, ...extra });
      setMsg({ text: "Saved. Logged to change history." });
      setAct(null);
      setLimitOpen(false);
      onSaved();
    } catch (e) {
      setMsg({ text: e instanceof Error ? e.message : "Failed", bad: true });
    } finally {
      setBusy(false);
    }
  }

  const state = c.blocked
    ? { word: "Bookings blocked", tone: "text-red-700" }
    : c.override_until
      ? { word: "Override active", tone: "text-amber-800" }
      : { word: "Can book", tone: "text-emerald-700" };

  const menu = ops.can_edit_money
    ? [
        {
          label: c.limit_cents != null ? "Change credit limit" : "Set credit limit",
          onSelect: () => setLimitOpen(true),
        },
        ...(c.blocked
          ? [{ label: "Allow bookings 48 h", onSelect: () => setAct("override" as Act) }]
          : []),
        ...(c.override_until
          ? [{ label: "End override", onSelect: () => setAct("clear_override" as Act) }]
          : []),
        ...(!held
          ? [
              {
                label: "Put on hold",
                tone: "danger" as const,
                onSelect: () => setAct("hold" as Act),
              },
            ]
          : []),
      ]
    : [];

  return (
    <Panel
      title="Credit"
      aside={
        <div className="flex items-center gap-2">
          {ops.can_edit_money && held ? (
            <PrimaryAction onClick={() => setAct("release")}>Release hold</PrimaryAction>
          ) : null}
          <ActionMenu label="Credit actions" items={menu} />
        </div>
      }
    >
      <p className={cn("text-2xl font-extrabold tracking-tight", state.tone)}>{state.word}</p>
      {c.reasons.length > 0 ? (
        <p className="mt-1 text-sm text-slate-700">{c.reasons.join(" · ")}</p>
      ) : null}

      <dl className="mt-6 grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-4">
        <Cell label="Overdue" value={cad(c.overdue_cents)} bad={c.overdue_cents > 0} />
        <Cell label="Outstanding" value={cad(c.outstanding_cents)} />
        <Cell label="Limit" value={c.limit_cents != null ? cad(c.limit_cents) : "None"} />
        <Cell
          label="Oldest overdue"
          value={c.oldest_overdue_days ? `${c.oldest_overdue_days} d` : "—"}
          bad={c.oldest_overdue_days > c.policy.grace_days}
        />
      </dl>

      <p className="mt-6 border-t border-primary/5 pt-4 text-sm text-slate-600">
        Holds start {c.policy.grace_days} days after an invoice is overdue and lift by themselves
        when the Interac e-Transfer is marked paid.
        {!ops.can_edit_money ? " Only admin, super admin or finance can change credit." : ""}
      </p>
      {msg ? (
        <p
          role="status"
          className={cn(
            "mt-3 text-sm font-semibold",
            msg.bad ? "text-red-700" : "text-emerald-700"
          )}
        >
          {msg.text}
        </p>
      ) : null}

      <ReasonDialog
        open={act != null}
        title={act ? COPY[act].title : ""}
        description={act ? COPY[act].body : undefined}
        confirm={act ? COPY[act].cta : ""}
        tone={act && COPY[act].danger ? "danger" : "default"}
        busy={busy}
        onCancel={() => setAct(null)}
        onConfirm={(reason) =>
          act && void run(act, act === "override" ? { override_days: 2 } : {}, reason)
        }
      />
      <Dialog
        open={limitOpen}
        onClose={() => setLimitOpen(false)}
        title="Credit limit"
        description="New bookings stop once the outstanding balance reaches the limit. Leave blank for no limit."
        footer={
          <>
            <QuietButton onClick={() => setLimitOpen(false)}>Cancel</QuietButton>
            <PrimaryAction
              disabled={busy || limitInvalid}
              onClick={() =>
                void run("limit", {
                  limit_cents: limitValue == null ? null : Math.round(limitValue * 100),
                })
              }
            >
              Save limit
            </PrimaryAction>
          </>
        }
      >
        <FieldLabel
          label="Limit (CAD)"
          hint={limitInvalid ? "Enter a positive amount." : undefined}
        >
          <input
            className={inputClass}
            inputMode="decimal"
            value={limit}
            aria-invalid={limitInvalid}
            onChange={(e) => setLimit(e.target.value.replace(/[^0-9.]/g, ""))}
            placeholder="No limit"
          />
        </FieldLabel>
      </Dialog>
    </Panel>
  );
}

function Cell({ label, value, bad }: { label: string; value: string; bad?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-semibold tracking-[0.14em] text-slate-600 uppercase">
        {label}
      </dt>
      <dd
        className={cn(
          "mt-1 truncate text-2xl font-extrabold tracking-tight tabular-nums",
          bad ? "text-red-700" : "text-primary"
        )}
      >
        {value}
      </dd>
    </div>
  );
}
