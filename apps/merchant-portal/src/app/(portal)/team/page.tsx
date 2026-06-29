"use client";

import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { inviteTeamMember, listTeam, removeTeamMember, type TeamMember } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useEffect, useState } from "react";

const ROLES = [
  { value: "merchant_owner", label: "Owner" },
  { value: "merchant_admin", label: "Manager" },
  { value: "merchant_ops", label: "Dispatcher" },
  { value: "merchant_finance", label: "Accounting" },
  { value: "merchant_readonly", label: "Viewer" },
];

export default function TeamPage() {
  const { getApiToken, orgId, isSignedIn, isLoaded } = useMerchantAuth();
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("merchant_ops");

  async function load() {
    const token = await getApiToken();
    setMembers(await listTeam(token, orgId));
  }

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch team on mount
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn, orgId]);

  async function onInvite(e: React.FormEvent) {
    e.preventDefault();
    const token = await getApiToken();
    await inviteTeamMember(token, email, role, orgId);
    setEmail("");
    await load();
  }

  async function onRemove(id: string) {
    const token = await getApiToken();
    await removeTeamMember(token, id, orgId);
    await load();
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-primary">Team Management</h1>

      <form
        onSubmit={onInvite}
        className="flex flex-wrap items-end gap-3 rounded-2xl border border-primary/10 bg-white p-6"
      >
        <div>
          <label className="text-sm font-medium">Email</label>
          <input
            type="email"
            required
            className="mt-1 block rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div>
          <label className="text-sm font-medium">Role</label>
          <select
            className="mt-1 block rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
        <Button type="submit">Invite user</Button>
      </form>

      <ul className="divide-y divide-primary/5 rounded-2xl border border-primary/10 bg-white">
        {members.map((m) => (
          <li key={m.id} className="flex items-center justify-between px-6 py-4 text-sm">
            <div>
              <p className="font-medium">{m.email}</p>
              <p className="text-xs text-muted">
                {ROLES.find((r) => r.value === m.role)?.label || m.role} · joined{" "}
                {formatDate(m.created_at)}
              </p>
            </div>
            <button type="button" className="text-xs text-red-600" onClick={() => onRemove(m.id)}>
              Remove
            </button>
          </li>
        ))}
        {members.length === 0 && (
          <li className="px-6 py-8 text-center text-muted">No team members</li>
        )}
      </ul>
    </div>
  );
}
