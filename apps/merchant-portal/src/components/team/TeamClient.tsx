"use client";

import Button from "@/components/ui/Button";
import { EmptyState } from "@porterchain/ui/empty-state";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { moduleLabel, seatStatusLabel } from "@/lib/catalog";
import {
  ROLE_OPTIONS,
  merchantRoleLabel,
  teamApi,
  type ActivityLogEntry,
  type PermissionsCatalog,
  type TeamMember,
  type TeamOverview,
  type TwoFactorStatus,
} from "@/lib/team";
import { contactsApi, type ContactInput, type MerchantContact } from "@/lib/contacts";
import { isClerkConfigured, useLocalDevAuth } from "@/lib/env";
import { merchantSignupUrl } from "@/lib/onboarding";
import { formatDate } from "@/lib/utils";
import { useUser, useClerk } from "@clerk/nextjs";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { startTransition, useCallback, useOptimistic, useState } from "react";

type Tab = "contacts" | "members" | "roles" | "activity" | "security";

const TABS: { id: Tab; label: string }[] = [
  { id: "contacts", label: "Contacts" },
  { id: "members", label: "Team access" },
  { id: "roles", label: "Roles & permissions" },
  { id: "activity", label: "Activity log" },
  { id: "security", label: "Two-factor auth" },
];

export default function TeamClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("contacts");
  const teamQuery = useQuery({
    queryKey: ["merchant-team", orgId ?? null],
    enabled: Boolean(isLoaded && isSignedIn),
    queryFn: async () => {
      const token = await getApiToken();
      const [overview, contacts, members, activity, roles, twoFactor] = await Promise.all([
        teamApi.overview(token, orgId),
        contactsApi.list(token, orgId),
        teamApi.members(token, orgId),
        teamApi.activity(token, orgId),
        teamApi.roles(token, orgId),
        teamApi.twoFactor(token, orgId),
      ]);
      return { overview, contacts, members, activity, roles, twoFactor };
    },
  });
  const overview = teamQuery.data?.overview ?? null;
  const contacts = teamQuery.data?.contacts ?? [];
  const members = teamQuery.data?.members ?? [];
  const activity = teamQuery.data?.activity ?? [];
  const roles = teamQuery.data?.roles ?? null;
  const twoFactor = teamQuery.data?.twoFactor ?? null;
  const error = teamQuery.error
    ? teamQuery.error instanceof Error
      ? teamQuery.error.message
      : "Failed to load team"
    : null;

  const load = useCallback(async () => {
    await qc.invalidateQueries({ queryKey: ["merchant-team", orgId ?? null] });
  }, [orgId, qc]);

  if (!overview && (!isLoaded || teamQuery.isLoading)) {
    if (error) {
      return <EmptyState title="Could not load team" hint={error} />;
    }
    return <PageSkeleton rows={4} />;
  }
  if (!overview) {
    return <EmptyState title="Could not load team" hint={error ?? "Team data is unavailable."} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Team</h1>
        <p className="mt-1 text-sm text-muted">
          {contacts.length} company contacts · {overview.member_count} portal seats · synced with
          admin
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <nav
        className="ops-tab-rail rounded-2xl border border-primary/10 bg-white"
        aria-label="Team sections"
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`min-h-10 shrink-0 rounded-xl px-3 py-1.5 text-sm font-medium whitespace-nowrap ${
              tab === t.id ? "bg-primary text-white" : "text-muted hover:bg-primary/5"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "contacts" && (
        <ContactsTab contacts={contacts} onRefresh={load} getToken={getApiToken} orgId={orgId} />
      )}
      {tab === "members" && (
        <MembersTab members={members} onRefresh={load} getToken={getApiToken} orgId={orgId} />
      )}
      {tab === "roles" && roles && <RolesTab catalog={roles} />}
      {tab === "activity" && <ActivityTab entries={activity} />}
      {tab === "security" && <SecurityTab status={twoFactor} />}
    </div>
  );
}

function ContactsTab({
  contacts,
  onRefresh,
  getToken,
  orgId,
}: {
  contacts: MerchantContact[];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const emptyForm: ContactInput = {
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    designation: "",
    department: "",
  };
  const [form, setForm] = useState<ContactInput>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const resetForm = () => {
    setForm(emptyForm);
    setEditingId(null);
    setError(null);
  };

  const startEdit = (contact: MerchantContact) => {
    setEditingId(contact.id);
    setForm({
      first_name: contact.first_name,
      last_name: contact.last_name ?? "",
      email: contact.email ?? "",
      phone: contact.phone ?? "",
      mobile: contact.mobile ?? "",
      designation: contact.designation ?? "",
      department: contact.department ?? "",
      is_primary: contact.is_primary,
    });
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const token = await getToken();
      const body: ContactInput = {
        first_name: form.first_name.trim(),
        last_name: form.last_name?.trim() || undefined,
        email: form.email?.trim() || undefined,
        phone: form.phone?.trim() || undefined,
        mobile: form.mobile?.trim() || undefined,
        designation: form.designation?.trim() || undefined,
        department: form.department?.trim() || undefined,
        is_primary: form.is_primary,
      };
      if (editingId) {
        await contactsApi.update(token, editingId, body, orgId);
      } else {
        await contactsApi.create(token, body, orgId);
      }
      resetForm();
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save contact");
    }
  };

  const remove = async (contact: MerchantContact) => {
    if (!contact.can_delete) {
      setError("Portal team members must be removed from the Team access tab.");
      return;
    }
    setError(null);
    try {
      const token = await getToken();
      await contactsApi.remove(token, contact.id, orgId);
      if (editingId === contact.id) resetForm();
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete contact");
    }
  };

  return (
    <div className="space-y-6">
      <form
        onSubmit={(e) => void save(e)}
        className="grid gap-3 rounded-2xl border border-primary/10 bg-white p-6 sm:grid-cols-2"
      >
        <div className="sm:col-span-2">
          <h2 className="font-semibold text-primary">
            {editingId ? "Edit contact" : "Add contact"}
          </h2>
          <p className="mt-1 text-xs text-muted">
            Contacts sync to Porterchain admin. Portal users appear here automatically from Team
            access.
          </p>
        </div>
        <Field label="First name" required>
          <input
            required
            className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={form.first_name}
            onChange={(e) => setForm({ ...form, first_name: e.target.value })}
          />
        </Field>
        <Field label="Last name">
          <input
            className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={form.last_name ?? ""}
            onChange={(e) => setForm({ ...form, last_name: e.target.value })}
          />
        </Field>
        <Field label="Email">
          <input
            type="email"
            className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={form.email ?? ""}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </Field>
        <Field label="Phone">
          <input
            className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={form.phone ?? ""}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
          />
        </Field>
        <Field label="Designation">
          <input
            className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={form.designation ?? ""}
            onChange={(e) => setForm({ ...form, designation: e.target.value })}
          />
        </Field>
        <Field label="Department">
          <input
            className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={form.department ?? ""}
            onChange={(e) => setForm({ ...form, department: e.target.value })}
          />
        </Field>
        <label className="flex items-center gap-2 text-sm sm:col-span-2">
          <input
            type="checkbox"
            checked={Boolean(form.is_primary)}
            onChange={(e) => setForm({ ...form, is_primary: e.target.checked })}
          />
          Primary contact
        </label>
        <div className="flex flex-wrap gap-2 sm:col-span-2">
          <Button type="submit">{editingId ? "Save changes" : "Add contact"}</Button>
          {editingId && (
            <Button type="button" variant="outline" onClick={resetForm}>
              Cancel
            </Button>
          )}
        </div>
        {error && <p className="text-sm text-red-600 sm:col-span-2">{error}</p>}
      </form>

      <ul className="divide-y divide-primary/5 rounded-2xl border border-primary/10 bg-white">
        {contacts.map((c) => (
          <li
            key={c.id}
            className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 text-sm"
          >
            <div>
              <p className="text-sm font-medium text-primary">
                {c.first_name} {c.last_name ?? ""}
                {c.is_primary && (
                  <span className="ml-2 rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                    Primary
                  </span>
                )}
                {(c.source === "team" || c.roles.includes("portal_team")) && (
                  <span className="ml-2 rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-800">
                    Portal team
                  </span>
                )}
              </p>
              <p className="text-xs text-muted">
                {[c.designation, c.email, c.phone].filter(Boolean).join(" · ") || "—"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => startEdit(c)}>
                Edit
              </Button>
              <button
                type="button"
                className="text-xs text-red-600 disabled:opacity-40"
                disabled={!c.can_delete}
                onClick={() => void remove(c)}
              >
                Delete
              </button>
            </div>
          </li>
        ))}
        {contacts.length === 0 && (
          <li className="px-6 py-8 text-center text-muted">No contacts yet</li>
        )}
      </ul>
    </div>
  );
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block text-sm font-medium text-primary">
      {label}
      {required && " *"}
      {children}
    </label>
  );
}

function MembersTab({
  members,
  onRefresh,
  getToken,
  orgId,
}: {
  members: TeamMember[];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("merchant_ops");
  const [optimisticMembers, applyOptimistic] = useOptimistic(
    members,
    (
      current: TeamMember[],
      action: { type: "role"; id: string; role: string } | { type: "remove"; id: string }
    ) => {
      if (action.type === "remove") return current.filter((m) => m.id !== action.id);
      return current.map((m) => (m.id === action.id ? { ...m, role: action.role } : m));
    }
  );

  const addSeat = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = await getToken();
    await teamApi.addSeat(token, email, role, orgId);
    setEmail("");
    await onRefresh();
  };

  const remove = (id: string) => {
    startTransition(async () => {
      applyOptimistic({ type: "remove", id });
      try {
        const token = await getToken();
        await teamApi.remove(token, id, orgId);
        await onRefresh();
      } catch {
        await onRefresh();
      }
    });
  };

  const changeRole = (id: string, newRole: string) => {
    startTransition(async () => {
      applyOptimistic({ type: "role", id, role: newRole });
      try {
        const token = await getToken();
        await teamApi.updateRole(token, id, newRole, orgId);
        await onRefresh();
      } catch {
        await onRefresh();
      }
    });
  };

  const reactivate = async (id: string) => {
    const token = await getToken();
    await teamApi.setActive(token, id, true, orgId);
    await onRefresh();
  };

  return (
    <div className="space-y-6">
      <form
        onSubmit={(e) => void addSeat(e)}
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
            placeholder="teammate@company.com"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Role</label>
          <select
            className="mt-1 block rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            {ROLE_OPTIONS.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
        <Button type="submit">Add teammate</Button>
      </form>
      <p className="text-xs text-muted">
        No invitation email is sent. Send them this link:{" "}
        <a href={merchantSignupUrl()} className="font-medium text-secondary underline">
          {merchantSignupUrl()}
        </a>
        . They sign up with the email above, and their password stays in Clerk.
      </p>

      <ul className="divide-y divide-primary/5 rounded-2xl border border-primary/10 bg-white">
        {optimisticMembers.map((m) => (
          <li
            key={m.id}
            className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 text-sm"
          >
            <div>
              <p className="font-medium">{m.email}</p>
              <p className="text-xs text-muted">
                {m.seat_status === "pending"
                  ? "Invited — they sign up with this email"
                  : m.seat_status === "off"
                    ? "Off"
                    : `Joined ${formatDate(m.created_at)}`}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={
                  m.seat_status === "pending"
                    ? "rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800"
                    : m.seat_status === "off"
                      ? "rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-semibold text-gray-600"
                      : "rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-semibold text-green-800"
                }
              >
                {m.seat_status_label ||
                  seatStatusLabel(m.seat_status || (m.is_active ? "active" : "off"))}
              </span>
              <select
                className="rounded-lg border border-primary/15 px-2 py-1 text-xs"
                value={m.role}
                disabled={m.seat_status === "off"}
                onChange={(e) => void changeRole(m.id, e.target.value)}
              >
                {ROLE_OPTIONS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
              {m.seat_status !== "off" && (
                <button
                  type="button"
                  className="text-xs text-red-600"
                  onClick={() => void remove(m.id)}
                >
                  Remove
                </button>
              )}
              {m.seat_status === "off" && (
                <button
                  type="button"
                  className="text-xs font-semibold text-secondary"
                  onClick={() => void reactivate(m.id)}
                >
                  Reactivate
                </button>
              )}
            </div>
          </li>
        ))}
        {optimisticMembers.length === 0 && (
          <li className="px-6 py-8 text-center text-muted">No team members</li>
        )}
      </ul>
    </div>
  );
}

function RolesTab({ catalog }: { catalog: PermissionsCatalog }) {
  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Roles</h2>
        <div className="mt-4 space-y-4">
          {catalog.roles.map((r) => (
            <div key={r.role} className="rounded-xl border border-primary/10 p-4">
              <p className="font-medium">{r.label}</p>
              <p className="mt-2 text-xs text-muted">
                {(r.module_labels?.length ? r.module_labels : r.modules.map(moduleLabel)).join(
                  " · "
                )}
              </p>
            </div>
          ))}
        </div>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Who can do what</h2>
        <table className="mt-4 w-full text-sm">
          <thead className="text-left text-muted">
            <tr>
              <th className="pb-2">Access</th>
              <th className="pb-2">Roles</th>
            </tr>
          </thead>
          <tbody>
            {catalog.modules.map((m) => (
              <tr key={m.module} className="border-t border-primary/5">
                <td className="py-2">{m.label || moduleLabel(m.module)}</td>
                <td className="py-2 text-xs text-muted">
                  {(m.role_labels?.length ? m.role_labels : m.roles.map(merchantRoleLabel)).join(
                    ", "
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function ActivityTab({ entries }: { entries: ActivityLogEntry[] }) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Activity log</h2>
      <ul className="mt-4 space-y-2 text-sm">
        {entries.length === 0 && <li className="text-muted">No activity yet</li>}
        {entries.map((e) => (
          <li key={e.id} className="flex justify-between gap-4 border-b border-primary/5 py-2">
            <span>
              <span className="font-medium">{e.summary || e.action}</span>
            </span>
            <span className="text-xs text-muted">
              {e.created_at ? formatDate(e.created_at) : "—"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SecurityTab({ status }: { status: TwoFactorStatus | null }) {
  const local = useLocalDevAuth();
  const clerkOn = isClerkConfigured() && !local;

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Two-factor authentication</h2>
      <p className="mt-2 text-sm text-muted">
        {status?.note ||
          "MFA is managed in your PorterChain sign-in account (Clerk), not as a portal toggle."}
      </p>
      {local ? (
        <p className="mt-4 text-sm text-muted">Local Clerk bypass does not use MFA.</p>
      ) : clerkOn ? (
        <ClerkMfaStatus />
      ) : (
        <p className="mt-4 text-sm text-muted">
          Sign-in is not configured, so MFA status is unavailable.
        </p>
      )}
    </section>
  );
}

function ClerkMfaStatus() {
  const { user, isLoaded } = useUser();
  const { openUserProfile } = useClerk();
  const enabled = Boolean(user?.twoFactorEnabled);

  return (
    <>
      <p className={`mt-4 text-sm ${enabled ? "text-green-700" : "text-muted"}`}>
        {!isLoaded
          ? "Checking your account…"
          : enabled
            ? "Your account has MFA enabled."
            : "Your account does not have MFA enabled yet."}
      </p>
      <button
        type="button"
        className="mt-3 text-sm font-medium text-secondary underline-offset-2 hover:underline"
        onClick={() => openUserProfile()}
      >
        Open account security
      </button>
    </>
  );
}
