"use client";

import { useState } from "react";
import { CheckCircle2, Circle, Mail, Rocket, UserPlus } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchants, type MerchantDetail } from "@/lib/merchants";
import { titleCase } from "@/lib/crmFormat";
import { Badge, Button, Field, Input, SectionCard, Select, Spinner } from "@/components/crm/primitives";

const MERCHANT_ROLES = [
  { value: "merchant_owner", label: "Owner" },
  { value: "merchant_admin", label: "Admin" },
  { value: "merchant_ops", label: "Operations" },
  { value: "merchant_finance", label: "Finance" },
  { value: "merchant_readonly", label: "Read only" },
] as const;

const INVITE_TONE: Record<string, "green" | "amber" | "red" | "slate"> = {
  accepted: "green",
  invite_pending: "amber",
  not_invited: "slate",
  invite_failed: "red",
  revoked: "red",
};

function inviteLabel(status: string | undefined) {
  if (!status) return "—";
  return status.replace(/_/g, " ");
}

export default function MerchantTeamPanel({ merchant }: { merchant: MerchantDetail }) {
  const { getApiToken } = useAdminAuth();
  const id = merchant.id;
  const [version, setVersion] = useState(0);
  const [ownerEmail, setOwnerEmail] = useState(merchant.email || "");
  const [memberEmail, setMemberEmail] = useState("");
  const [memberRole, setMemberRole] = useState("merchant_ops");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const { data: onboarding, error: onboardingError } = useApiData(
    (t) => merchants.onboarding(t, id),
    [id, version],
    { key: `merchant-onboarding-${id}` }
  );
  const { data: team } = useApiData((t) => merchants.team(t, id), [id, version], {
    key: `merchant-team-${id}`,
  });

  const refresh = () => setVersion((v) => v + 1);

  async function run(action: string, fn: () => Promise<void>) {
    setBusy(action);
    setError(null);
    setSuccess(null);
    try {
      await fn();
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  async function inviteOwner() {
    const email = ownerEmail.trim();
    if (!email) return;
    await run("invite-owner", async () => {
      const token = await getApiToken();
      await merchants.inviteOwner(token, id, email);
      setSuccess(`Invitation sent to ${email}`);
    });
  }

  async function inviteMember() {
    const email = memberEmail.trim();
    if (!email) return;
    await run("invite-member", async () => {
      const token = await getApiToken();
      await merchants.inviteTeamMember(token, id, email, memberRole);
      setMemberEmail("");
      setSuccess(`Invitation sent to ${email}`);
    });
  }

  async function approveMerchant() {
    await run("approve", async () => {
      const token = await getApiToken();
      await merchants.approve(token, id);
      setSuccess("Merchant approved — portal access enabled");
    });
  }

  async function resendInvite(email: string, role: string) {
    await run(`resend-${email}`, async () => {
      const token = await getApiToken();
      if (role === "merchant_owner") {
        await merchants.inviteOwner(token, id, email);
      } else {
        await merchants.inviteTeamMember(token, id, email, role);
      }
      setSuccess(`Invitation resent to ${email}`);
    });
  }

  if (onboardingError) {
    return <p className="text-sm text-red-600">{onboardingError}</p>;
  }

  if (!onboarding?.steps) {
    return <Spinner label="Loading onboarding…" />;
  }

  const steps = onboarding.steps;
  const blockers = onboarding.blockers ?? [];

  return (
    <div className="space-y-5">
      <SectionCard title="Portal onboarding">
        <div className="space-y-4 px-5 py-4">
          <p className="text-sm text-muted">
            Provision the merchant owner, send a Clerk invitation, then approve the account. No need to use Settings →
            Users for this merchant.
          </p>

          <ul className="space-y-2">
            {steps.map((step) => (
              <li key={step.id} className="flex items-center gap-2 text-sm">
                {step.complete ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />
                ) : (
                  <Circle className="h-4 w-4 shrink-0 text-muted" />
                )}
                <span className={step.complete ? "text-primary" : "text-muted"}>{step.label}</span>
              </li>
            ))}
          </ul>

          {onboarding.ready ? (
            <Badge tone="green">Ready for merchant portal</Badge>
          ) : (
            <Badge tone="amber">{blockers.length} step(s) remaining</Badge>
          )}

          <div className="flex flex-wrap items-end gap-3 rounded-xl border border-primary/10 bg-gray-bg/40 p-4">
            <Field label="Owner email" className="min-w-[16rem] flex-1">
              <Input
                type="email"
                value={ownerEmail}
                onChange={(e) => setOwnerEmail(e.target.value)}
                placeholder={onboarding.owner_email}
              />
            </Field>
            <Button
              onClick={() => void inviteOwner()}
              disabled={!ownerEmail.trim() || busy === "invite-owner"}
            >
              <Mail className="h-4 w-4" />
              {onboarding.team_count === 0 ? "Invite owner" : "Send / resend invite"}
            </Button>
            {onboarding.can_approve && (
              <Button
                variant="outline"
                onClick={() => void approveMerchant()}
                disabled={busy === "approve"}
              >
                <Rocket className="h-4 w-4" />
                Approve merchant
              </Button>
            )}
            {!onboarding.ready && (
              <Button
                onClick={() =>
                  void run("complete", async () => {
                    const token = await getApiToken();
                    await merchants.completeOnboarding(
                      token,
                      id,
                      ownerEmail.trim() || onboarding.owner_email
                    );
                    setSuccess("Onboarding completed — merchant activated");
                  })
                }
                disabled={busy === "complete"}
              >
                <Rocket className="h-4 w-4" />
                Complete onboarding
              </Button>
            )}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
          {success && <p className="text-sm text-green-700">{success}</p>}
        </div>
      </SectionCard>

      <SectionCard
        title={`Team (${team?.length ?? 0})`}
        action={
          <div className="flex flex-wrap items-end gap-2">
            <Field label="Email" className="min-w-[12rem]">
              <Input
                type="email"
                value={memberEmail}
                onChange={(e) => setMemberEmail(e.target.value)}
                placeholder="teammate@company.com"
              />
            </Field>
            <Field label="Role" className="min-w-[8rem]">
              <Select value={memberRole} onChange={(e) => setMemberRole(e.target.value)}>
                {MERCHANT_ROLES.filter((r) => r.value !== "merchant_owner").map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Button
              variant="outline"
              disabled={!memberEmail.trim() || busy === "invite-member"}
              onClick={() => void inviteMember()}
            >
              <UserPlus className="h-4 w-4" />
              Invite
            </Button>
          </div>
        }
      >
        <div className="divide-y divide-primary/5">
          {(team ?? []).map((u) => (
            <div key={u.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
              <div>
                <p className="text-sm font-medium text-primary">{u.email}</p>
                <p className="text-xs text-muted">{titleCase(u.role.replace(/_/g, " "))}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={u.is_active ? "green" : "slate"}>{u.is_active ? "Active" : "Inactive"}</Badge>
                <Badge tone={INVITE_TONE[u.invite_status ?? ""] ?? "slate"}>
                  {inviteLabel(u.invite_status)}
                </Badge>
                {u.clerk_linked && <Badge tone="green">Clerk linked</Badge>}
                {u.invite_status !== "accepted" && (
                  <Button
                    variant="ghost"
                    className="text-xs"
                    disabled={busy === `resend-${u.email}`}
                    onClick={() => void resendInvite(u.email, u.role)}
                  >
                    Resend invite
                  </Button>
                )}
                {!u.is_active && (
                  <Button
                    variant="ghost"
                    className="text-xs"
                    disabled={busy === `activate-${u.email}`}
                    onClick={() =>
                      void run(`activate-${u.email}`, async () => {
                        const token = await getApiToken();
                        await merchants.activateUsers(token, id, u.email);
                        setSuccess(`${u.email} re-enabled`);
                      })
                    }
                  >
                    Enable user
                  </Button>
                )}
              </div>
            </div>
          ))}
          {(!team || team.length === 0) && (
            <p className="px-5 py-10 text-center text-sm text-muted">
              No team members yet. Invite the owner above to start onboarding.
            </p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
