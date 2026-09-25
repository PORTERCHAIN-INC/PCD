"use client";

import { useState } from "react";
import { Mail, Send } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { drivers, type DriverDetail } from "@/lib/drivers";
import { Button, SectionCard } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";

export function SettingsTab({
  d,
  canWrite,
  onChanged,
}: {
  d: DriverDetail;
  canWrite: boolean;
  onChanged: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  async function decide(
    docType: string,
    decision: "verified" | "rejected" | "cleared",
    reason?: string
  ) {
    setBusy(true);
    try {
      const token = await getApiToken();
      await drivers.decideDocument(token, d.id, { doc_type: docType, decision, reason });
      onChanged();
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Document update failed");
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(false);
    }
  }

  async function verify(patch: Record<string, boolean | string>) {
    setBusy(true);
    try {
      const token = await getApiToken();
      await drivers.verify(token, d.id, patch);
      onChanged();
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Verify failed");
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(false);
    }
  }
  async function action(type: string) {
    setBusy(true);
    try {
      const token = await getApiToken();
      const res = await drivers.action(token, d.id, { type });
      if (res.delivery_status === "logged") {
        setToast(
          `${titleCase(type)} logged only — not delivered` + (res.detail ? ` (${res.detail})` : ".")
        );
      } else {
        setToast(`${titleCase(type)} queued.`);
      }
      setTimeout(() => setToast(null), 3500);
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Action failed");
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(false);
    }
  }
  async function resendInvite() {
    setBusy(true);
    try {
      const token = await getApiToken();
      await drivers.invite(token, d.id);
      setToast("Invite resent.");
      setTimeout(() => setToast(null), 2500);
      onChanged();
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Invite failed");
      setTimeout(() => setToast(null), 3500);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-5 md:grid-cols-2">
      <SectionCard title="Verification & compliance">
        <div className="space-y-2 p-5">
          {canWrite ? (
            <>
              <ToggleRow
                label="License verified"
                value={d.license_verified}
                onToggle={() => void decide("license", d.license_verified ? "cleared" : "verified")}
                busy={busy}
              />
              <ToggleRow
                label="Insurance verified"
                value={d.insurance_verified}
                onToggle={() =>
                  void decide("insurance", d.insurance_verified ? "cleared" : "verified")
                }
                busy={busy}
              />
              <ToggleRow
                label="Vehicle verified"
                value={d.vehicle_verified}
                onToggle={() =>
                  void decide("vehicle_registration", d.vehicle_verified ? "cleared" : "verified")
                }
                busy={busy}
              />
              <ToggleRow
                label="Medical transport certified"
                value={Boolean(d.medical_transport_certified)}
                onToggle={() =>
                  verify({ medical_transport_certified: !d.medical_transport_certified })
                }
                busy={busy}
              />
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-primary">Background check</span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    className="px-2 py-1 text-xs"
                    onClick={() => void decide("background_check", "verified")}
                    disabled={busy}
                  >
                    Pass
                  </Button>
                  <Button
                    variant="outline"
                    className="px-2 py-1 text-xs"
                    onClick={() =>
                      void decide("background_check", "rejected", "Background check failed.")
                    }
                    disabled={busy}
                  >
                    Fail
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted">
              License {d.license_verified ? "verified" : "not verified"}. Insurance{" "}
              {d.insurance_verified ? "verified" : "not verified"}. Vehicle{" "}
              {d.vehicle_verified ? "verified" : "not verified"}. Background{" "}
              {d.background_check_status || "pending"}.
            </p>
          )}
          {toast && <p className="text-sm text-muted">{toast}</p>}
        </div>
      </SectionCard>
      {canWrite && (
        <SectionCard title="Operations">
          <div className="flex flex-wrap gap-2 p-5">
            <Button variant="outline" onClick={() => action("push")} disabled={busy}>
              <Send className="h-4 w-4" /> Send push
            </Button>
            <Button variant="outline" onClick={() => action("sms")} disabled={busy}>
              <Send className="h-4 w-4" /> Send SMS
            </Button>
            <Button variant="outline" onClick={() => action("email")} disabled={busy}>
              <Mail className="h-4 w-4" /> Email driver
            </Button>
            <Button variant="outline" onClick={resendInvite} disabled={busy}>
              <Mail className="h-4 w-4" /> Resend invite
            </Button>
          </div>
        </SectionCard>
      )}
    </div>
  );
}

function ToggleRow({
  label,
  value,
  onToggle,
  busy,
}: {
  label: string;
  value: boolean;
  onToggle: () => void;
  busy: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-sm text-primary">{label}</span>
      <button
        onClick={onToggle}
        disabled={busy}
        className={cn(
          "rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset",
          value
            ? "bg-green-50 text-green-700 ring-green-600/20"
            : "bg-amber-50 text-amber-700 ring-amber-600/20"
        )}
      >
        {value ? "Verified" : "Mark verified"}
      </button>
    </div>
  );
}
