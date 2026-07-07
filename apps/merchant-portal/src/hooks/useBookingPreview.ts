"use client";

import { useEffect, useRef, useState } from "react";
import type { BookDeliveryPayload } from "@/lib/api";
import { previewBooking, type BookingPreview } from "@/lib/booking";

export function useBookingPreview(
  token: string | null,
  orgId: string | undefined,
  payload: BookDeliveryPayload | null,
  enabled: boolean
) {
  const [preview, setPreview] = useState<BookingPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!enabled || !token || !payload) {
      setPreview(null);
      return;
    }
    if (!payload.pickup.formatted?.trim() || !payload.dropoff.formatted?.trim()) {
      setPreview(null);
      return;
    }
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await previewBooking(token, payload, orgId);
        setPreview(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Preview failed");
        setPreview(null);
      } finally {
        setLoading(false);
      }
    }, 450);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [token, orgId, payload, enabled]);

  return { preview, loading, error };
}
