"use client";

import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { Badge, Button, Field, Input, Modal } from "@/components/crm/primitives";
import { settingsApi, type PlatformUser } from "@/lib/settings";
import { withStaffStepUp } from "@/lib/staff-step-up";
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
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteOk, setInviteOk] = useState<string | null>(null);
  const [authorizeResult, setAuthorizeResult] = useState<{
    modules: string[];
    actions_taken: string[];
  } | null>(null);

  const hasClerk = Boolean(user.clerk_user_id && !user.clerk_user_id.startsWith("pending:"));
  const canAuthorize = user.access_status !== "authorized" || !user.provisioned;
  const platformId =
    user.provisioned && !user.id.startsWith("clerk:")
      ? user.id
      : user.id.startsWith("clerk:")
        ? user.id
        : undefined;

  async function authorizeDriver() {
    setBusy(true);
    setAuthorizeError(null);
    setAuthorizeResult(null);
    try {
      const token = await requireApiToken(getApiToken);
      const result = await withStaffStepUp(token, () =>
        settingsApi.authorizeUser(token, "driver", {
          platform_user_id: platformId,
          clerk_user_id: hasClerk ? (user.clerk_user_id ?? undefined) : undefined,
          email: user.email,
          name: name.trim() || user.name || undefined,
        })
      );
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

  async function sendInvite() {
    if (!platformId || platformId.startsWith("clerk:")) {
      setInviteError("Create a PorterChain driver row before inviting.");
      return;
    }
    setBusy(true);
    setInviteError(null);
    setInviteOk(null);
    try {
      const token = await requireApiToken(getApiToken);
      await withStaffStepUp(token, () => settingsApi.inviteUser(token, "driver", platformId));
      setInviteOk("Clerk invitation sent.");
      onSaved();
    } catch (e) {
      setInviteError(e instanceof Error ? e.message : "Invite failed");
    } finally {
      setBusy(false);
    }
  }

  async function save(patch: { password?: string; banned?: boolean }) {
    if (!hasClerk || !user.clerk_user_id) return;
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
    if (!confirm(`Remove driver ${user.email}? This cannot be undone.`)) return;
    setBusy(true);
    try {
      const id = user.provisioned && !user.id.startsWith("clerk:") ? user.id : undefined;
      await settingsApi.deleteDriver(await requireApiToken(getApiToken), {
        clerk_user_id: hasClerk ? (user.clerk_user_id ?? undefined) : undefined,
        platform_user_id: id,
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
          {hasClerk && (
            <Button disabled={busy} onClick={() => void save({ password: password || undefined })}>
              {busy ? "Saving…" : "Save"}
            </Button>
          )}
        </>
      }
    >
      <div className="space-y-4 text-sm">
        <p className="text-muted">
          {hasClerk ? (
            <>
              Clerk ID: <code className="rounded bg-gray-bg px-1">{user.clerk_user_id}</code>
            </>
          ) : (
            <>
              No Clerk link yet — authorize for dispatch, then send a Clerk invite when they need
              portal/mobile login.
            </>
          )}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-muted">Portal access:</span>
          <Badge tone={accessTone(user.access_status)}>{accessLabel(user.access_status)}</Badge>
          {!user.provisioned && <Badge tone="amber">Not provisioned in Porterchain</Badge>}
          {!hasClerk && <Badge tone="red">Not in Clerk</Badge>}
        </div>

        <div className="rounded-xl border border-secondary/20 bg-secondary/5 p-4">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-secondary" />
            <div className="min-w-0 flex-1 space-y-3">
              <div>
                <p className="font-semibold text-primary">Authorize driver</p>
                <p className="mt-1 text-muted">
                  Approves the driver for dispatch and portal access. Does not require Clerk —
                  invite separately for login.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" disabled={busy} onClick={() => void authorizeDriver()}>
                  {busy
                    ? "Authorizing…"
                    : canAuthorize
                      ? "Authorize driver"
                      : "Re-check authorization"}
                </Button>
                {platformId && !platformId.startsWith("clerk:") && (
                  <Button variant="outline" disabled={busy} onClick={() => void sendInvite()}>
                    {busy ? "Sending…" : hasClerk ? "Re-send Clerk invite" : "Send Clerk invite"}
                  </Button>
                )}
              </div>
              {authorizeResult && (
                <div className="space-y-2 text-xs">
                  <p className="font-medium text-primary">
                    {authorizeResult.actions_taken.join(" · ")}
                  </p>
                  <p className="text-muted">Modules: {authorizeResult.modules.join(", ") || "—"}</p>
                </div>
              )}
              {inviteOk && <p className="text-xs text-green-700">{inviteOk}</p>}
              {authorizeError && <p className="text-xs text-red-600">{authorizeError}</p>}
              {inviteError && <p className="text-xs text-red-600">{inviteError}</p>}
            </div>
          </div>
        </div>

        <Field label="Display name">
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        {hasClerk && (
          <>
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
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => void save({ banned: false })}
                >
                  Unban
                </Button>
              ) : (
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => void save({ banned: true })}
                >
                  Ban in Clerk
                </Button>
              )}
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
