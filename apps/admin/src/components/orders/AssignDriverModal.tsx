"use client";

import { useEffect, useState } from "react";
import { Button, Modal, Spinner } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { api } from "@/lib/api";
import { ops, type SuggestedDriver } from "@/lib/operations";
import { titleCase } from "@/lib/crmFormat";
import { formatSuggestionEta } from "@/lib/telemetryLabels";

type Props = {
  open: boolean;
  orderId: string | null;
  trackingNumber?: string | null;
  currentDriverName?: string | null;
  onClose: () => void;
  onAssigned?: () => void;
};

export function AssignDriverModal({
  open,
  orderId,
  trackingNumber,
  currentDriverName,
  onClose,
  onAssigned,
}: Props) {
  const { getApiToken } = useAdminAuth();
  const [drivers, setDrivers] = useState<SuggestedDriver[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState("");
  const [unranked, setUnranked] = useState(false);

  useEffect(() => {
    if (!open || !orderId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setSelected("");
    setUnranked(false);
    void (async () => {
      try {
        const token = await getApiToken();
        let suggestions = await ops.driverSuggestions(token, orderId);
        if (suggestions.source === "pending") {
          for (let i = 0; i < 10; i += 1) {
            await new Promise((r) => setTimeout(r, 1000));
            if (cancelled) return;
            suggestions = await ops.driverSuggestions(token, orderId);
            if (suggestions.source !== "pending") break;
          }
        }
        if (cancelled) return;
        if (suggestions.drivers?.length) {
          setDrivers(suggestions.drivers);
          setUnranked(false);
        } else if (suggestions.medical_required) {
          setDrivers([]);
          setError(
            suggestions.filtered_out_count
              ? `No medical-certified drivers available (${suggestions.filtered_out_count} filtered out).`
              : "This order requires a medical-transport certified driver."
          );
        } else {
          const fallback = await ops.assignableDrivers(token);
          if (cancelled) return;
          const rows = suggestions.medical_required
            ? fallback.filter((d) =>
                Boolean(
                  (d as { medical_transport_certified?: boolean }).medical_transport_certified
                )
              )
            : fallback;
          setUnranked(suggestions.source === "pending" || !suggestions.drivers?.length);
          setDrivers(
            rows.map((d) => ({
              id: d.id,
              name: d.name,
              rating: d.rating,
              online: Boolean(d.is_online),
              active_orders: d.active_orders ?? 0,
              eta_minutes: null,
              deadhead_km: null,
              eta_source: "none",
              capability_match: null,
              score: 0,
              reasons: [],
            }))
          );
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Could not load drivers");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, orderId, getApiToken]);

  async function confirm() {
    if (!orderId || !selected) return;
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      await api.assignDriver(token, orderId, selected);
      onAssigned?.();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Assign failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={currentDriverName ? "Reassign driver" : "Assign driver"}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={() => void confirm()} disabled={!selected || busy || loading}>
            {busy ? "Assigning…" : currentDriverName ? "Reassign" : "Assign"}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <p className="text-sm text-muted">
          {trackingNumber ? (
            <>
              Ranked drivers for{" "}
              <span className="font-mono font-medium text-primary">{trackingNumber}</span>
              {currentDriverName ? (
                <>
                  {" "}
                  · current <span className="text-primary">{currentDriverName}</span>
                </>
              ) : null}
            </>
          ) : (
            "Select a driver. Scores use ETA, load, and rating when available."
          )}
        </p>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {unranked && !loading && (
          <p className="text-xs font-medium text-amber-700">Unranked — ETAs not ready</p>
        )}
        {loading ? (
          <Spinner label="Ranking drivers…" />
        ) : drivers.length === 0 ? (
          <p className="text-sm text-muted">No assignable drivers found.</p>
        ) : (
          <ul className="max-h-72 space-y-2 overflow-y-auto">
            {drivers.map((d) => {
              const active = selected === d.id;
              return (
                <li key={d.id}>
                  <button
                    type="button"
                    onClick={() => setSelected(d.id)}
                    className={`flex w-full items-start justify-between gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors ${
                      active
                        ? "border-secondary bg-secondary/5"
                        : "border-primary/10 hover:bg-gray-bg"
                    }`}
                  >
                    <div>
                      <p className="text-sm font-semibold text-primary">{d.name}</p>
                      <p className="mt-0.5 text-xs text-muted">
                        {d.online ? "Online" : "Offline"}
                        {d.active_orders != null ? ` · ${d.active_orders} active` : ""}
                        {` · ${formatSuggestionEta(d.eta_minutes, d.eta_source)}`}
                        {d.deadhead_km != null ? ` · ${d.deadhead_km.toFixed(1)} km` : ""}
                      </p>
                      {d.reasons?.length > 0 && (
                        <p className="mt-1 text-[11px] text-muted">
                          {d.reasons.slice(0, 2).join(" · ")}
                        </p>
                      )}
                    </div>
                    <div className="shrink-0 text-right">
                      {d.score > 0 && (
                        <p className="text-xs font-semibold text-secondary">
                          {Math.round(d.score)}
                        </p>
                      )}
                      {d.rating != null && (
                        <p className="text-[11px] text-muted">{titleCase(String(d.rating))}</p>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </Modal>
  );
}
