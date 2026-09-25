"use client";

import { useState } from "react";
import Link from "next/link";
import { Button, Field, Input, Modal } from "@/components/crm/primitives";
import { settingsApi } from "@/lib/settings";
import { requireApiToken } from "../requireApiToken";

export function CreateDriverModal({
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
  const [password, setPassword] = useState("");
  const [sendInvite, setSendInvite] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdHref, setCreatedHref] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    setCreatedHref(null);
    try {
      const created = await settingsApi.createDriver(await requireApiToken(getApiToken), {
        email: email.trim(),
        name: name.trim() || undefined,
        password: password.trim() || undefined,
        send_invite: sendInvite && !password.trim(),
      });
      const id =
        (typeof created.platform_user_id === "string" && created.platform_user_id) ||
        (typeof created.driver_id === "string" && created.driver_id) ||
        (typeof created.id === "string" && created.id) ||
        null;
      if (id) setCreatedHref(`/drivers/${id}`);
      onCreated();
      setEmail("");
      setName("");
      setPassword("");
      setSendInvite(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add driver (identity)"
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            {createdHref ? "Close" : "Cancel"}
          </Button>
          {!createdHref && (
            <Button disabled={!email.trim() || busy} onClick={() => void submit()}>
              {busy ? "Saving…" : "Create PENDING driver"}
            </Button>
          )}
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-muted">
          Creates a PENDING driver in PorterChain. Uncheck invite to create without Clerk (authorize
          and assign jobs immediately). Check invite to email Clerk login when they need the portal.
          Full compliance profile:{" "}
          <Link href="/drivers" className="font-medium text-secondary hover:underline">
            Drivers → Add driver
          </Link>
          .
        </p>
        <Field label="Email">
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Name">
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Password (optional)">
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Set in Clerk — never shown again"
            autoComplete="new-password"
          />
        </Field>
        {!password && (
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={sendInvite}
              onChange={(e) => setSendInvite(e.target.checked)}
            />
            Send Clerk invitation email (required for portal login; optional for ops)
          </label>
        )}
        {createdHref && (
          <p className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
            Driver created.{" "}
            <Link href={createdHref} className="font-semibold underline">
              Open driver 360
            </Link>
          </p>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </Modal>
  );
}
