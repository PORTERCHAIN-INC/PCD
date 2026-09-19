"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Button, Field, Input, Modal, Select } from "@/components/crm/primitives";
import { useApiData } from "@/hooks/useApiData";
import { merchants } from "@/lib/merchants";
import { MERCHANT_SEAT_ROLES, settingsApi } from "@/lib/settings";
import { requireApiToken } from "../requireApiToken";

export function AddMerchantSeatModal({
  open,
  getApiToken,
  onClose,
  onCreated,
}: {
  open: boolean;
  getApiToken: () => Promise<string | null>;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [merchantId, setMerchantId] = useState("");
  const [merchantSearch, setMerchantSearch] = useState("");
  const [role, setRole] = useState("merchant_ops");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdHref, setCreatedHref] = useState<string | null>(null);

  const { data: merchantRows } = useApiData((t) => merchants.list(t, { limit: "500" }), [open], {
    key: "settings-merchant-picker",
    enabled: open,
  });

  const options = useMemo(() => {
    const rows = merchantRows ?? [];
    const q = merchantSearch.trim().toLowerCase();
    const filtered = q
      ? rows.filter(
          (m) =>
            m.company_name.toLowerCase().includes(q) ||
            (m.email ?? "").toLowerCase().includes(q) ||
            m.id.toLowerCase().includes(q)
        )
      : rows;
    return filtered.slice(0, 50);
  }, [merchantRows, merchantSearch]);

  async function submit() {
    setBusy(true);
    setError(null);
    setCreatedHref(null);
    try {
      await settingsApi.addMerchantSeat(await requireApiToken(getApiToken), {
        email: email.trim(),
        name: name.trim() || undefined,
        merchant_id: merchantId.trim(),
        role,
      });
      setCreatedHref(`/merchants/${merchantId.trim()}`);
      onCreated();
      setEmail("");
      setName("");
      setRole("merchant_ops");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Seat reserve failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add merchant seat"
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            {createdHref ? "Close" : "Cancel"}
          </Button>
          {!createdHref && (
            <Button
              disabled={!email.trim() || !merchantId.trim() || busy}
              onClick={() => void submit()}
            >
              {busy ? "Saving…" : "Reserve seat"}
            </Button>
          )}
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-muted">
          Reserves a seat by email on an existing merchant. Prefer Team on the merchant 360 for
          day-to-day seats —{" "}
          <Link href="/merchants" className="font-medium text-secondary hover:underline">
            open Merchants
          </Link>
          .
        </p>
        <Field label="Email">
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Name">
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Find merchant">
          <Input
            value={merchantSearch}
            onChange={(e) => setMerchantSearch(e.target.value)}
            placeholder="Search name, email, or id"
          />
        </Field>
        <Field label="Merchant">
          <Select value={merchantId} onChange={(e) => setMerchantId(e.target.value)}>
            <option value="">Select merchant…</option>
            {options.map((m) => (
              <option key={m.id} value={m.id}>
                {m.company_name} ({m.status})
              </option>
            ))}
          </Select>
        </Field>
        {merchantId && (
          <p className="text-xs text-muted">
            Selected id: <code>{merchantId}</code> ·{" "}
            <Link
              href={`/merchants/${merchantId}`}
              className="text-secondary hover:underline"
              target="_blank"
            >
              Open merchant 360
            </Link>
          </p>
        )}
        <Field label="Merchant role">
          <Select value={role} onChange={(e) => setRole(e.target.value)}>
            {MERCHANT_SEAT_ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </Select>
        </Field>
        {createdHref && (
          <p className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
            Seat reserved.{" "}
            <Link href={createdHref} className="font-semibold underline">
              Open merchant team
            </Link>
          </p>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </Modal>
  );
}
