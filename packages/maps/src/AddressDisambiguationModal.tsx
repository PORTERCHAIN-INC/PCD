"use client";

import { Suspense, lazy, useEffect, useId, useMemo, useState } from "react";
import AddressAutocompleteInput from "./AddressAutocompleteInput";
import type { BookingAddress } from "./types";

const LibreMap = lazy(() => import("./LibreMap"));

/** One ranked suggestion from the API's shared geo_resolve (matches Candidate.to_dict()). */
export interface AddressCandidate {
  formatted: string;
  lat: number;
  lng: number;
  city?: string | null;
  postal?: string | null;
  province?: string | null;
  fsa?: string | null;
  score?: number;
  source?: string;
  place_id?: string | null;
}

export interface AddressDisambiguationModalProps {
  open: boolean;
  /** The address as the user/file gave it. */
  originalAddress: string;
  candidates: AddressCandidate[];
  /** e.g. "Stop 3" — shown under the title. */
  contextLabel?: string;
  busy?: boolean;
  error?: string | null;
  /** Small PMTiles map of the candidates (lazy-loaded). Default true. */
  showMap?: boolean;
  apiBase?: string;
  onPickCandidate: (index: number, candidate: AddressCandidate) => void;
  /** place is set when the user picked an autocomplete suggestion (pin locked). */
  onUpdateAddress: (address: string, place: BookingAddress | null) => void;
  onClose: () => void;
}

export const ADDRESS_DISAMBIGUATION_TITLE =
  "We can't confidently understand this address — please pick or update";

export function candidateFsa(c: AddressCandidate): string {
  if (c.fsa) return c.fsa;
  const m = /\b([A-Z]\d[A-Z])\s?\d[A-Z]\d\b/i.exec(`${c.postal ?? ""} ${c.formatted ?? ""}`);
  return m ? m[1].toUpperCase() : "";
}

export default function AddressDisambiguationModal({
  open,
  originalAddress,
  candidates,
  contextLabel,
  busy = false,
  error,
  showMap = true,
  apiBase,
  onPickCandidate,
  onUpdateAddress,
  onClose,
}: AddressDisambiguationModalProps) {
  const titleId = useId();
  const [selected, setSelected] = useState<number | null>(null);
  const [edit, setEdit] = useState(originalAddress);
  const [place, setPlace] = useState<BookingAddress | null>(null);

  useEffect(() => {
    if (!open) return;
    setSelected(candidates.length ? 0 : null);
    setEdit(originalAddress);
    setPlace(null);
  }, [open, originalAddress, candidates]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, busy, onClose]);

  const markers = useMemo(
    () =>
      candidates
        .filter((c) => Number.isFinite(c.lat) && Number.isFinite(c.lng))
        .map((c, i) => ({
          position: { lat: c.lat, lng: c.lng },
          kind: (i === selected ? "pickup" : "dropoff") as "pickup" | "dropoff",
          title: `${i + 1}. ${c.formatted}`,
        })),
    [candidates, selected]
  );

  if (!open) return null;
  const chosen = selected != null ? candidates[selected] : undefined;

  return (
    <div
      role="presentation"
      onClick={() => !busy && onClose()}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: "rgba(10,22,40,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        data-testid="address-disambiguation-modal"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#fff",
          borderRadius: 20,
          width: "min(640px, 100%)",
          maxHeight: "90vh",
          overflowY: "auto",
          padding: 20,
          boxShadow: "0 24px 64px rgba(10,22,40,0.25)",
        }}
      >
        <h2 id={titleId} style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>
          {ADDRESS_DISAMBIGUATION_TITLE}
        </h2>
        <p style={{ margin: "6px 0 14px", fontSize: 13, color: "#55657a" }}>
          {contextLabel ? `${contextLabel}: ` : ""}
          <strong>{originalAddress || "(blank)"}</strong>
          {candidates.length > 1 ? ` matches ${candidates.length} places.` : ""}
        </p>

        {candidates.length > 0 && (
          <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
            <legend style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
              Pick the right one
            </legend>
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 6 }}>
              {candidates.map((c, i) => {
                const fsa = candidateFsa(c);
                const on = i === selected;
                return (
                  <li key={`${c.place_id ?? c.formatted}-${i}`}>
                    <label
                      style={{
                        display: "flex",
                        gap: 10,
                        alignItems: "flex-start",
                        padding: "8px 10px",
                        borderRadius: 12,
                        cursor: "pointer",
                        border: on ? "2px solid #0a1628" : "1px solid rgba(10,22,40,0.15)",
                      }}
                    >
                      <input
                        type="radio"
                        name={`${titleId}-cand`}
                        checked={on}
                        onChange={() => setSelected(i)}
                      />
                      <span style={{ fontSize: 14 }}>
                        <span style={{ display: "block", fontWeight: 600 }}>{c.formatted}</span>
                        <span style={{ fontSize: 12, color: "#55657a" }}>
                          {[c.city, fsa && `FSA ${fsa}`, c.source].filter(Boolean).join(" · ")}
                        </span>
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          </fieldset>
        )}

        {showMap && markers.length > 0 && (
          <div style={{ marginTop: 12, height: 180, borderRadius: 12, overflow: "hidden" }}>
            <Suspense fallback={null}>
              <LibreMap
                markers={markers}
                fitPoints={markers.map((m) => m.position)}
                minFitPoints={1}
                fitPadding={32}
                gestureHandling="cooperative"
                style={{ width: "100%", height: "100%" }}
              />
            </Suspense>
          </div>
        )}

        <div style={{ marginTop: 16 }}>
          <label htmlFor={`${titleId}-edit`} style={{ fontSize: 13, fontWeight: 600 }}>
            Or update the address
          </label>
          <div style={{ position: "relative", marginTop: 6 }}>
            <AddressAutocompleteInput
              id={`${titleId}-edit`}
              value={edit}
              apiBase={apiBase}
              onChange={(v) => {
                setEdit(v);
                setPlace(null);
              }}
              onPlaceSelect={(p) => {
                setEdit(p.formatted);
                setPlace(p);
              }}
              placeholder="Start typing — pick a suggestion to lock the pin"
              className="w-full"
              fallbackClassName="w-full rounded-xl border border-primary/15 px-3 py-2"
            />
          </div>
        </div>

        {error && (
          <p role="alert" style={{ marginTop: 10, fontSize: 13, color: "#b42318" }}>
            {error}
          </p>
        )}

        <div
          style={{
            marginTop: 18,
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
            justifyContent: "flex-end",
          }}
        >
          <button type="button" onClick={onClose} disabled={busy} style={btn(false)}>
            Later
          </button>
          <button
            type="button"
            disabled={busy || !edit.trim() || (edit.trim() === originalAddress.trim() && !place)}
            onClick={() => onUpdateAddress(edit.trim(), place)}
            style={btn(false)}
          >
            Update address
          </button>
          <button
            type="button"
            disabled={busy || selected == null || !chosen}
            onClick={() => selected != null && chosen && onPickCandidate(selected, chosen)}
            style={btn(true)}
          >
            Use this place
          </button>
        </div>
      </div>
    </div>
  );
}

function btn(primary: boolean): React.CSSProperties {
  return {
    padding: "8px 14px",
    borderRadius: 9999,
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
    border: primary ? "none" : "1px solid rgba(10,22,40,0.2)",
    background: primary ? "#0a1628" : "#fff",
    color: primary ? "#fff" : "#0a1628",
  };
}
