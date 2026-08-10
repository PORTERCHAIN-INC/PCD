"use client";

import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { Badge, Button, Field, Input, Modal } from "@/components/crm/primitives";
import { settingsApi, type PlatformUser } from "@/lib/settings";
import { requireApiToken } from "../requireApiToken";
import { accessLabel, accessTone } from "../status";

export function ManageDriverModal({
  user,
  getApiToken,
  onClose,
  onSaved,
}: {
  user: PlatformUser;
  getApiToken: () => Promise<string | null>;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(user.name ?? "");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [authorizeError, setAuthorizeError] = useState<string | null>(null);
  const [authorizeResult, setAuthorizeResult] = useState<{
    modules: string[];
    actions_taken: string[];
  } | null>(null);

  const canAuthorize = user.access_status !== "authorized" || !user.provisioned;

  async function authorizeDriver() {
    setBusy(true);
    setAuthorizeError(null);
    setAuthorizeResult(null);
    try {
      const platformId =
        user.provisioned && !user.id.startsWith("clerk:")
          ? user.id
          : user.id.startsWith("clerk:")
            ? user.id
            : undefined;
      const result = await settingsApi.authorizeDriver(await requireApiToken(getApiToken), {
        platform_user_id: platformId,
        clerk_user_id: user.clerk_user_id ?? undefined,
        email: user.email,
        name: name.trim() || user.name || undefined,
      });
      setAuthorizeResult({
        modules: result.modules,
        actions_taken: result.actions_taken,
      });
      onSaved();
    } catch (e) {
      setAuthorizeError(e instanceof Error ? e.message : "Authorization failed");
    } finally {
      setBusy(false);
    }
  }

  async function save(patch: { password?: string; banned?: boolean }) {
    if (!user.clerk_user_id) return;
    setBusy(true);
    try {
      await settingsApi.updateDriverClerk(await requireApiToken(getApiToken), {
        clerk_user_id: user.clerk_user_id,
        name: name.trim() || undefined,
        password: patch.password,
        banned: patch.banned,
      });
      onSaved();
      onClose();
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!confirm(`Delete Clerk user ${user.email}? This cannot be undone.`)) return;
    setBusy(true);
    try {
      const platformId = user.provisioned && !user.id.startsWith("clerk:") ? user.id : undefined;
      await settingsApi.deleteDriver(await requireApiToken(getApiToken), {
        clerk_user_id: user.clerk_user_id ?? undefined,
        platform_user_id: platformId,
      });
      onSaved();
      onClose();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Manage driver — ${user.email}`}
      footer={
        <>
          <Button
            variant="ghost"
            className="text-red-600"
            disabled={busy}
            onClick={() => void remove()}
          >
            Delete
          </Button>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={busy} onClick={() => void save({ password: password || undefined })}>
            {busy ? "Saving…" : "Save"}
          </Button>
        </>
      }
    >
      <div className="space-y-4 text-sm">
        <p className="text-muted">
          Clerk ID: <code className="rounded bg-gray-bg px-1">{user.clerk_user_id}</code>
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-muted">Portal access:</span>
          <Badge tone={accessTone(user.access_status)}>{accessLabel(user.access_status)}</Badge>
          {!user.provisioned && <Badge tone="amber">Not provisioned in Porterchain</Badge>}
        </div>

        <div className="rounded-xl border border-secondary/20 bg-secondary/5 p-4">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-secondary" />
            <div className="min-w-0 flex-1 space-y-3">
              <div>
                <p className="font-semibold text-primary">Authorize driver portal</p>
                <p className="mt-1 text-muted">
                  Approves the driver for full driver portal and mobile access.
                </p>
                <p className="mt-2 text-xs text-muted">
                  Target role: <code className="rounded bg-white px-1">approved</code>
                </p>
              </div>
              <Button variant="outline" disabled={busy} onClick={() => void authorizeDriver()}>
                {busy
                  ? "Authorizing…"
                  : canAuthorize
                    ? "Authorize driver"
                    : "Re-check authorization"}
              </Button>
              {authorizeResult && (
                <div className="space-y-2 text-xs">
                  <p className="font-medium text-primary">
                    {authorizeResult.actions_taken.join(" · ")}
                  </p>
                  <p className="text-muted">Modules: {authorizeResult.modules.join(", ") || "—"}</p>
                </div>
              )}
              {authorizeError && <p className="text-xs text-red-600">{authorizeError}</p>}
            </div>
          </div>
        </div>

        <Field label="Display name">
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="New password">
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Resets password in Clerk"
            autoComplete="new-password"
          />
        </Field>
        <div className="flex flex-wrap gap-2">
          {user.clerk_status === "banned" ? (
            <Button variant="outline" disabled={busy} onClick={() => void save({ banned: false })}>
              Unban
            </Button>
          ) : (
            <Button variant="outline" disabled={busy} onClick={() => void save({ banned: true })}>
              Ban in Clerk
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
