"use client";

import { useState } from "react";
import { ListOrdered } from "lucide-react";
import { driverApi } from "@/lib/api";
import { actionErrorMessage } from "@/lib/jobs";
import {
  isMidStopId,
  isMultiStop,
  midStopButtons,
  stopAddress,
  stopStatusLabel,
  stopTitle,
  type OrderStop,
} from "@/lib/multi-stops";
import { cn } from "@/lib/utils";

/** Every stop of a multi-stop order, in order; middle stops are worked right here. */
export function OrderStops({
  stops,
  routeId,
  onUpdated,
}: {
  stops: OrderStop[] | null | undefined;
  routeId: string;
  onUpdated: () => void;
}) {
  const [pending, setPending] = useState<string | null>(null);
  const [proof, setProof] = useState("");
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null);
  if (!isMultiStop(stops)) return null;
  const list = stops ?? [];

  async function act(stop: OrderStop, key: string) {
    setPending(`${stop.stop_id}:${key}`);
    setMessage(null);
    try {
      if (key === "start_delivery") await driverApi.startDelivery(routeId, stop.stop_id);
      if (key === "arrive") await driverApi.arriveStop(routeId, stop.stop_id);
      if (key === "complete") {
        if (stop.stop_type !== "pickup") {
          const value = proof.trim();
          if (!value) throw new Error("pod_required");
          if (/^(https?:|data:)/.test(value))
            await driverApi.podPhoto(routeId, stop.stop_id, value);
          else await driverApi.podSignature(routeId, stop.stop_id, value);
        }
        await driverApi.deliverStop(routeId, stop.stop_id);
        setProof("");
      }
      setMessage({ text: `${stopTitle(stop, list.indexOf(stop))}: done`, error: false });
      onUpdated();
    } catch (e) {
      const raw = e instanceof Error ? e.message : "action_failed";
      setMessage({ text: actionErrorMessage(raw), error: true });
    } finally {
      setPending(null);
    }
  }

  return (
    <section className="rounded-2xl bg-white p-5 shadow-sm" data-testid="order-stops">
      <h2 className="flex items-center gap-2 text-lg font-bold">
        <ListOrdered className="h-5 w-5 text-[var(--secondary)]" />
        All stops ({list.length})
      </h2>
      {message ? (
        <p className={cn("mt-2 text-sm", message.error ? "text-red-700" : "text-emerald-700")}>
          {message.text}
        </p>
      ) : null}
      <ol className="mt-4 space-y-3">
        {list.map((stop, i) => {
          const buttons = midStopButtons(stop);
          const current = (stop.actions ?? []).length > 0;
          const done = stop.status === "picked_up" || stop.status === "delivered";
          return (
            <li
              key={stop.stop_id}
              data-testid={`order-stop-${i + 1}`}
              className={cn(
                "rounded-xl border p-3",
                current ? "border-[var(--secondary)] bg-[var(--secondary)]/5" : "border-gray-200",
                done && "opacity-70"
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-bold">{stopTitle(stop, i)}</p>
                  <p className="text-sm text-[var(--muted)]">{stopAddress(stop)}</p>
                </div>
                <span
                  className={cn(
                    "shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold",
                    done
                      ? "bg-emerald-100 text-emerald-800"
                      : current
                        ? "bg-amber-100 text-amber-900"
                        : "bg-gray-100 text-gray-700"
                  )}
                >
                  {current && !done ? "Now" : stopStatusLabel(stop.status)}
                </span>
              </div>
              {current && !isMidStopId(stop.stop_id) ? (
                <p className="mt-2 text-xs text-[var(--muted)]">
                  Use the next action above for this stop.
                </p>
              ) : null}
              {buttons.length ? (
                <div className="mt-3 space-y-2">
                  {stop.stop_type !== "pickup" && buttons.some((b) => b.key === "complete") ? (
                    <input
                      value={proof}
                      onChange={(e) => setProof(e.target.value)}
                      placeholder="Photo URL or receiver's name (signature)"
                      className="w-full rounded-xl border px-3 py-2 text-sm"
                      aria-label="Proof for this drop"
                    />
                  ) : null}
                  <div className="flex flex-wrap gap-2">
                    {buttons.map((b) => (
                      <button
                        key={b.key}
                        type="button"
                        disabled={Boolean(pending)}
                        onClick={() => act(stop, b.key)}
                        className={cn(
                          "rounded-xl px-4 py-2 text-sm font-bold text-white disabled:opacity-50",
                          b.key === "complete" ? "bg-emerald-600" : "bg-[var(--primary)]"
                        )}
                      >
                        {pending === `${stop.stop_id}:${b.key}` ? "Working…" : b.label}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
