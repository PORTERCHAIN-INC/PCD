"use client";

import { useState } from "react";
import { CheckCircle2, Circle, Mail, Rocket, UserPlus } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchants, type MerchantDetail } from "@/lib/merchants";
import { inviteStatusLabel, seatStatusLabel } from "@/lib/catalog";
import { titleCase } from "@/lib/crmFormat";
import {
  Badge,
  Button,
  Field,
  Input,
  SectionCard,
  Select,
  Spinner,
} from "@/components/crm/primitives";
import { MERCHANT_SEAT_ROLES } from "@/lib/settings";

const INVITE_TONE: Record<string, "green" | "amber" | "red" | "slate"> = {
  accepted: "green",
  invite_pending: "amber",
  not_invited: "slate",
  invite_failed: "red",
  revoked: "red",
};

function inviteLabel(status: string | undefined) {
  return inviteStatusLabel(status);
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
      setSuccess(`Owner seat reserved for ${email} — they sign up on Platform with this email`);
    });
  }

  async function inviteMember() {
    const email = memberEmail.trim();
    if (!email) return;
    await run("invite-member", async () => {
      const token = await getApiToken();
      await merchants.inviteTeamMember(token, id, email, memberRole);
      setMemberEmail("");
      setSuccess(`Teammate seat reserved for ${email}`);
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
      setSuccess(`Seat re-reserved for ${email}`);
    });
  }

  async function changeRole(userId: string, role: string) {
    await run(`role-${userId}`, async () => {
      const token = await getApiToken();
      await merchants.updateTeamRole(token, id, userId, role);
      setSuccess("Role updated");
    });
  }

  async function removeMember(userId: string, email: string) {
    if (!confirm(`Deactivate seat for ${email}?`)) return;
    await run(`remove-${userId}`, async () => {
      const token = await getApiToken();
      await merchants.removeTeamMember(token, id, userId);
      setSuccess(`${email} deactivated`);
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
            Reserve the owner seat by email, have them create their PorterChain Platform account,
            then approve the merchant. No Clerk invitation email is sent.
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
              {onboarding.team_count === 0 ? "Add owner seat" : "Refresh owner seat"}
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
                {MERCHANT_SEAT_ROLES.filter((r) => r.value !== "merchant_owner").map((r) => (
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
              Add teammate
            </Button>
          </div>
        }
      >
        <div className="divide-y divide-primary/5">
          {(team ?? []).map((u) => (
            <div key={u.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
              <div>
                <p className="text-sm font-medium text-primary">{u.email}</p>
                <p className="text-xs text-muted">
                  {u.role_label || titleCase(u.role.replace(/_/g, " "))}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  tone={
                    u.seat_status === "pending"
                      ? "amber"
                      : u.seat_status === "off" || !u.is_active
                        ? "slate"
                        : "green"
                  }
                >
                  {u.seat_status_label ||
                    seatStatusLabel(u.seat_status || (u.is_active ? "active" : "off"))}
                </Badge>
                <Badge tone={INVITE_TONE[u.invite_status ?? ""] ?? "slate"}>
                  {u.invite_status_label || inviteLabel(u.invite_status)}
                </Badge>
                {u.clerk_linked && <Badge tone="green">Clerk linked</Badge>}
                {u.is_active && (
                  <Select
                    value={u.role}
                    className="min-w-[9rem] text-xs"
                    disabled={busy === `role-${u.id}`}
                    onChange={(e) => void changeRole(u.id, e.target.value)}
                  >
                    {MERCHANT_SEAT_ROLES.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </Select>
                )}
                {u.invite_status !== "accepted" && (
                  <Button
                    variant="ghost"
                    className="text-xs"
                    disabled={busy === `resend-${u.email}`}
                    onClick={() => void resendInvite(u.email, u.role)}
                  >
                    Re-reserve seat
                  </Button>
                )}
                {u.is_active && (
                  <Button
                    variant="ghost"
                    className="text-xs text-red-600"
                    disabled={busy === `remove-${u.id}`}
                    onClick={() => void removeMember(u.id, u.email)}
                  >
                    Remove
                  </Button>
                )}
                {!u.is_active && (
                  <Button
                    variant="ghost"
                    className="text-xs"
                    disabled={busy === `reactivate-${u.id}`}
                    onClick={() =>
                      void run(`reactivate-${u.id}`, async () => {
                        const token = await getApiToken();
                        await merchants.setTeamActive(token, id, u.id, true);
                        setSuccess(`${u.email} reactivated`);
                      })
                    }
                  >
                    Reactivate seat
                  </Button>
                )}
              </div>
            </div>
          ))}
          {(!team || team.length === 0) && (
            <p className="px-5 py-10 text-center text-sm text-muted">
              No team members yet. Add the owner seat above to start onboarding.
            </p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
