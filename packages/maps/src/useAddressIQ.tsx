"use client";

import { useCallback, useRef, useState, type ReactNode } from "react";
import AddressDisambiguationModal, { type AddressCandidate } from "./AddressDisambiguationModal";
import { resolveGeoAddress } from "./maps-core";
import type { BookingAddress } from "./types";

/** One address field to check before booking. */
export interface AddressIQField {
  /** Stable id so callers can map results back (e.g. "pickup", "drop-2"). */
  key: string;
  /** Shown under the modal title, e.g. "Dropoff 2". */
  label: string;
  address: BookingAddress;
}

type Pending = {
  field: AddressIQField;
  candidates: AddressCandidate[];
  resolve: (a: BookingAddress | null) => void;
};

/**
 * Shared address brain for every booking surface (customer, admin, merchant).
 * A typed address that was never picked from suggestions (no lat) goes through
 * geo_resolve: confident -> pinned; ambiguous / weak / not found ->
 * AddressDisambiguationModal (never a silent guess).
 *
 * `check(fields)` resolves to the updated addresses keyed by field.key, or null
 * when the user closed the modal (booking should stop). If the resolver is
 * offline the field is returned unchanged (old server-side path).
 */
export function useAddressIQ(opts: { apiBase?: string } = {}): {
  check: (fields: AddressIQField[]) => Promise<Record<string, BookingAddress> | null>;
  checking: boolean;
  modal: ReactNode;
} {
  const [pending, setPending] = useState<Pending | null>(null);
  const [checking, setChecking] = useState(false);
  const apiBase = useRef(opts.apiBase);
  apiBase.current = opts.apiBase;

  const ask = (field: AddressIQField, candidates: AddressCandidate[]) =>
    new Promise<BookingAddress | null>((resolve) => setPending({ field, candidates, resolve }));

  const resolveOne = useCallback(async (field: AddressIQField): Promise<BookingAddress | null> => {
    let a = field.address;
    // Loop: an edited (typed, unpicked) address is resolved again.
    for (;;) {
      if (!a.formatted?.trim() || typeof a.lat === "number") return a;
      const r = await resolveGeoAddress(a.formatted, { apiBase: apiBase.current }).catch(
        () => null
      );
      if (!r) return a;
      const best = r.candidates?.[0];
      if (r.status === "confident" && best) {
        return {
          ...a,
          lat: best.lat,
          lng: best.lng,
          postal: a.postal ?? best.postal ?? undefined,
        };
      }
      const picked = await ask({ ...field, address: a }, r.candidates ?? []);
      if (!picked) return null;
      a = picked;
    }
  }, []);

  const check = useCallback(
    async (fields: AddressIQField[]) => {
      setChecking(true);
      try {
        const out: Record<string, BookingAddress> = {};
        for (const f of fields) {
          const r = await resolveOne(f);
          if (!r) return null;
          out[f.key] = r;
        }
        return out;
      } finally {
        setChecking(false);
      }
    },
    [resolveOne]
  );

  const finish = (a: BookingAddress | null) => {
    const p = pending;
    setPending(null);
    p?.resolve(a);
  };

  const modal = (
    <AddressDisambiguationModal
      open={pending !== null}
      originalAddress={pending?.field.address.formatted ?? ""}
      candidates={pending?.candidates ?? []}
      contextLabel={pending?.field.label}
      apiBase={opts.apiBase}
      onPickCandidate={(_i, c) =>
        finish({
          formatted: c.formatted,
          lat: c.lat,
          lng: c.lng,
          postal: c.postal ?? undefined,
          placeId: c.place_id ?? undefined,
        })
      }
      onUpdateAddress={(text, place) => {
        if (place && typeof place.lat === "number") finish(place);
        else if (text.trim()) finish({ formatted: text.trim() });
      }}
      onClose={() => finish(null)}
    />
  );

  return { check, checking, modal };
}
