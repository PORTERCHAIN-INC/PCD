"use client";

import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { createBooking } from "@/lib/api";
import Link from "next/link";
import { useState } from "react";

export default function BookPage() {
  const { getApiToken, orgId, isSignedIn } = useMerchantAuth();
  const [pickup, setPickup] = useState("");
  const [dropoff, setDropoff] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [internalRef, setInternalRef] = useState("");
  const [poNumber, setPoNumber] = useState("");
  const [costCentre, setCostCentre] = useState("");
  const [instructions, setInstructions] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      const order = await createBooking(
        token,
        {
          pickup: { formatted: pickup },
          dropoff: { formatted: dropoff },
          scheduled_at: new Date(scheduledAt || Date.now()).toISOString(),
          internal_reference: internalRef || undefined,
          purchase_order_number: poNumber || undefined,
          cost_centre: costCentre || undefined,
          special_instructions: instructions || undefined,
        },
        orgId
      );
      setResult(order.tracking_number);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Booking failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Book Delivery</h1>
        <p className="text-sm text-muted">Net terms booking — no upfront payment required</p>
      </div>

      {result ? (
        <div className="rounded-2xl border border-green-200 bg-green-50 p-6">
          <p className="font-semibold text-green-800">Booking confirmed</p>
          <p className="mt-2 text-sm">
            Tracking: <span className="font-mono">{result}</span>
          </p>
          <div className="mt-4 flex gap-3">
            <Link href={`/track?q=${result}`} className="text-sm text-secondary hover:underline">
              Track shipment
            </Link>
            <button type="button" className="text-sm text-muted hover:underline" onClick={() => setResult(null)}>
              Book another
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6">
          <Field label="Pickup address" value={pickup} onChange={setPickup} required />
          <Field label="Dropoff address" value={dropoff} onChange={setDropoff} required />
          <Field label="Scheduled at" type="datetime-local" value={scheduledAt} onChange={setScheduledAt} required />
          <Field label="Internal reference" value={internalRef} onChange={setInternalRef} />
          <Field label="Purchase order number" value={poNumber} onChange={setPoNumber} />
          <Field label="Cost centre" value={costCentre} onChange={setCostCentre} />
          <div>
            <label className="text-sm font-medium text-primary">Special instructions</label>
            <textarea
              className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
              rows={3}
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" disabled={loading}>
            {loading ? "Booking…" : "Confirm Booking"}
          </Button>
        </form>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label className="text-sm font-medium text-primary">{label}</label>
      <input
        type={type}
        required={required}
        className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
