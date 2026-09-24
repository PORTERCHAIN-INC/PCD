"use client";

import { useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { customersApi, type CreateCustomerResult } from "@/lib/customers";
import { Button, Field, Input, Modal } from "@/components/crm/primitives";

type Props = {
  open: boolean;
  onClose: () => void;
  onCreated: (result: CreateCustomerResult) => void;
  getApiToken?: () => Promise<string | null>;
};

export function CustomerCreateModal({
  open,
  onClose,
  onCreated,
  getApiToken: getTokenProp,
}: Props) {
  const auth = useAdminAuth();
  const getApiToken = getTokenProp ?? auth.getApiToken;
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [sendInvite, setSendInvite] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setEmail("");
    setFullName("");
    setPhone("");
    setSendInvite(false);
    setError(null);
    setBusy(false);
  }

  function handleClose() {
    if (busy) return;
    reset();
    onClose();
  }

  async function submit() {
    const trimmed = email.trim();
    if (!trimmed || !trimmed.includes("@")) {
      setError("Enter a valid email");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      if (!token) throw new Error("Not signed in");
      const result = await customersApi.create(token, {
        email: trimmed,
        full_name: fullName.trim() || null,
        phone: phone.trim() || null,
        send_invite: sendInvite,
      });
      reset();
      onCreated(result);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not create customer";
      if (msg === "customer_email_exists") {
        setError("A Clerk-linked customer already uses this email — open them from the list.");
      } else if (msg === "clerk_not_configured") {
        setError(
          "Platform Clerk is not configured — create without invite, or configure customer Clerk keys."
        );
      } else {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Create customer"
      footer={
        <>
          <Button variant="outline" onClick={handleClose} disabled={busy}>
            Cancel
          </Button>
          <Button disabled={!email.trim() || busy} onClick={() => void submit()}>
            {busy ? "Creating…" : "Create customer"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-muted">
          Creates a retail customer for phone-book orders and care. They stay orphan until they
          accept a Clerk invite or self SignUp on the customer portal.
        </p>
        <Field label="Email">
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="customer@example.com"
            autoFocus
          />
        </Field>
        <Field label="Full name (optional)">
          <Input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Alex Rivera"
          />
        </Field>
        <Field label="Phone (optional)">
          <Input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+1 416 555 0100"
          />
        </Field>
        <label className="flex items-start gap-2 text-sm text-primary">
          <input
            type="checkbox"
            className="mt-1"
            checked={sendInvite}
            onChange={(e) => setSendInvite(e.target.checked)}
          />
          <span>
            Send Platform Clerk invite to sign up
            <span className="block text-xs text-muted">
              Requires Platform Clerk keys. Leave unchecked for phone-book only (orphan row).
            </span>
          </span>
        </label>
        {sendInvite && (
          <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            Invite fails with <code>clerk_not_configured</code> if customer Clerk secrets are
            missing in this environment.
          </p>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </Modal>
  );
}
