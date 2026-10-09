"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  cleanInstructions,
  manageErrorText,
  type DeliveryInstructions,
  type DeliveryManageOptions,
} from "@porterchain/types";
import Container from "@/components/ui/Container";
import {
  getDeliveryManageOptions,
  postDeliveryInstructions,
  postDeliverySchedule,
  type ManageApiError,
} from "@/lib/api";

function errorCode(err: unknown): string | null {
  return (err as ManageApiError | null)?.code ?? null;
}

export default function ManageView({ tracking }: { tracking: string }) {
  const token = useSearchParams().get("t") ?? "";
  const [opts, setOpts] = useState<DeliveryManageOptions | null>(null);
  const [error, setError] = useState<string | null>(token ? null : manageErrorText("link_invalid"));
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [windowCode, setWindowCode] = useState("");
  const [form, setForm] = useState<DeliveryInstructions>({});

  useEffect(() => {
    if (!token) return;
    getDeliveryManageOptions(tracking, token)
      .then((o) => {
        setOpts(o);
        setForm(o.instructions ?? {});
        setWindowCode(o.schedule?.code ?? "");
      })
      .catch((err) => setError(manageErrorText(errorCode(err))));
  }, [tracking, token]);

  async function save(kind: "schedule" | "instructions") {
    if (!opts) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const next =
        kind === "schedule"
          ? await postDeliverySchedule(tracking, token, windowCode)
          : await postDeliveryInstructions(tracking, token, cleanInstructions(form, opts.rules));
      setOpts(next);
      setNotice(kind === "schedule" ? "Delivery time saved." : "Instructions saved.");
    } catch (err) {
      setError(manageErrorText(errorCode(err)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Container className="py-12 md:py-20 max-w-lg">
      <h1 className="type-h2 font-bold text-primary mb-2">Manage your delivery</h1>
      <p className="type-caption text-muted font-mono mb-6">{tracking}</p>
      {error ? (
        <p role="alert" className="mb-6 text-red-600">
          {error}
        </p>
      ) : null}
      {notice ? (
        <p role="status" className="mb-6 text-green-700">
          {notice}
        </p>
      ) : null}
      {opts ? (
        <div className="space-y-8">
          {opts.rules.id_required ? (
            <p className="type-small rounded-xl border border-amber-200 bg-amber-50 p-3">
              Photo ID is required at delivery.
            </p>
          ) : null}
          <section>
            <h2 className="type-h4 font-semibold mb-3">Delivery time</h2>
            {opts.can_reschedule && opts.windows.length ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void save("schedule");
                }}
                className="space-y-2"
              >
                {opts.windows.map((w) => (
                  <label
                    key={w.code}
                    className="flex min-h-11 items-center gap-3 rounded-xl border border-primary/10 px-4 py-2"
                  >
                    <input
                      type="radio"
                      name="window"
                      value={w.code}
                      checked={windowCode === w.code}
                      onChange={() => setWindowCode(w.code)}
                    />
                    <span className="type-small">{w.label}</span>
                  </label>
                ))}
                <button
                  type="submit"
                  disabled={busy || !windowCode}
                  className="mt-2 rounded-xl bg-secondary px-4 py-2.5 font-semibold text-white type-small disabled:opacity-50"
                >
                  Save delivery time
                </button>
              </form>
            ) : (
              <p className="type-small text-muted">
                {opts.schedule?.label
                  ? `Booked for ${opts.schedule.label}.`
                  : "This delivery can no longer be rescheduled online."}
              </p>
            )}
          </section>
          {opts.can_edit_instructions ? (
            <section>
              <h2 className="type-h4 font-semibold mb-3">Instructions for the driver</h2>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void save("instructions");
                }}
                className="space-y-3"
              >
                {(
                  [
                    ["gate_code", "Gate code", 32],
                    ["buzzer", "Buzzer / unit", 32],
                    ...(opts.rules.safe_place_allowed
                      ? ([["safe_place", "Safe place (if no one is home)", 120]] as const)
                      : []),
                    ["notes", "Other notes", 280],
                  ] as const
                ).map(([key, label, max]) => (
                  <label key={key} className="block">
                    <span className="type-small text-muted">{label}</span>
                    <input
                      className="mt-1 w-full min-h-11 rounded-xl border border-primary/20 px-3"
                      maxLength={max}
                      value={form[key] ?? ""}
                      onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    />
                  </label>
                ))}
                {!opts.rules.safe_place_allowed ? (
                  <p className="type-caption text-muted">
                    This sender needs the parcel handed to a person, so a safe place is not
                    available.
                  </p>
                ) : null}
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-xl bg-secondary px-4 py-2.5 font-semibold text-white type-small disabled:opacity-50"
                >
                  Save instructions
                </button>
              </form>
            </section>
          ) : null}
          <p className="type-caption text-muted">
            Your gate code and instructions are only shared with the driver for this delivery.
          </p>
        </div>
      ) : null}
    </Container>
  );
}
