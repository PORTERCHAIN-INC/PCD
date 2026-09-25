"use client";

import { useState } from "react";
import { Button, Field, Input, Modal } from "@/components/crm/primitives";
import { settingsApi } from "@/lib/settings";
import { withStaffStepUp } from "@/lib/staff-step-up";
import { requireApiToken } from "@/components/settings/panels/users/requireApiToken";

export type ImpersonationTargetType = "driver" | "merchant" | "customer";

/** Relative portal path only — blocks open redirects. */
function safeNextPath(raw: string | undefined): string | null {
  const next = (raw || "").trim();
  if (!next.startsWith("/") || next.startsWith("//")) return null;
  return next;
}

export function ImpersonateModal({
  open,
  targetType,
  targetId,
  targetLabel,
  getApiToken,
  onClose,
  nextPath,
}: {
  open: boolean;
  targetType: ImpersonationTargetType;
  targetId: string;
  targetLabel: string;
  getApiToken: () => Promise<string | null>;
  onClose: () => void;
  /** Optional post-bootstrap path in the target portal (e.g. `/api?tab=keys`). */
  nextPath?: string;
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const token = await requireApiToken(getApiToken);
      const session = await withStaffStepUp(token, () =>
        settingsApi.startImpersonation(token, {
          target_type: targetType,
          target_id: targetId,
          reason: reason.trim(),
        })
      );
      if (session.portal_bootstrap_url) {
        const next = safeNextPath(nextPath);
        let href = session.portal_bootstrap_url;
        if (next) {
          try {
            const u = new URL(href);
            u.searchParams.set("next", next);
            href = u.toString();
          } catch {
            /* keep bootstrap URL as returned */
          }
        }
        window.open(href, "_blank", "noopener,noreferrer");
      }
      onClose();
      setReason("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Impersonation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Open as user (audited)"
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={busy || reason.trim().length < 10} onClick={() => void start()}>
            {busy ? "Starting…" : "Start 15-min session"}
          </Button>
        </>
      }
    >
      <div className="space-y-4 text-sm">
        <p className="text-muted">
          Break-glass only. Opens the {targetType} portal as{" "}
          <strong className="text-primary">{targetLabel}</strong> with a short-lived audited token
          (not a forged Clerk login). Every start is written to the admin audit log.
        </p>
        <Field label="Reason (required, min 10 characters)">
          <Input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Support ticket #1842 — verify missing payouts screen"
            autoFocus
          />
        </Field>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </Modal>
  );
}
