"use client";

import { useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  Mail,
  Search,
  Shield,
  ShieldCheck,
  Truck,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import {
  Avatar,
  Badge,
  Button,
  Field,
  Input,
  Modal,
  Select,
  Spinner,
} from "@/components/crm/primitives";
import { shortDate } from "@/lib/crmFormat";
import {
  ACCESS_STATUS_OPTIONS,
  ADMIN_ROLES,
  CLERK_STATUS_OPTIONS,
  IDENTITY_STATUS_OPTIONS,
  INVITE_STATUS_OPTIONS,
  settingsApi,
  type PlatformUser,
  type PlatformUsersFacets,
  type StaffUser,
  type UserDirectoryFilters,
  type UserDirectoryTab,
} from "@/lib/settings";
import { SECTION_DESCRIPTIONS } from "@/lib/settings-metadata";
import { SettingsCard, SettingsPageHeader } from "../ui/SettingsPrimitives";

async function requireApiToken(getApiToken: () => Promise<string | null>): Promise<string> {
  const token = await getApiToken();
  if (!token) throw new Error("unauthorized");
  return token;
}

const USER_TABS: Array<{
  id: UserDirectoryTab;
  label: string;
  icon: typeof Users;
  description: string;
}> = [
  { id: "staff", label: "Staff", icon: Shield, description: "Internal ops — admin portal access" },
  {
    id: "driver",
    label: "Drivers",
    icon: Truck,
    description: "Fleet drivers — driver portal & mobile",
  },
  {
    id: "merchant",
    label: "Merchants",
    icon: Building2,
    description: "B2B portal users by organization",
  },
  {
    id: "customer",
    label: "Customers",
    icon: Users,
    description: "Retail customers — website & customer portal",
  },
];

const EMPTY_FILTERS: UserDirectoryFilters = {};

function accessTone(s: string): "green" | "amber" | "red" | "slate" | "sky" {
  if (s === "authorized") return "green";
  if (s === "pending_review" || s === "invite_pending") return "amber";
  if (s === "suspended" || s === "not_authorized" || s === "inactive" || s === "merchant_inactive")
    return "red";
  return "slate";
}

function inviteTone(s: string): "green" | "amber" | "red" | "slate" | "sky" {
  if (s === "accepted") return "green";
  if (s === "invite_pending") return "amber";
  if (s === "not_invited") return "slate";
  if (s === "revoked" || s === "invite_failed") return "red";
  return "sky";
}

function identityTone(s: string): "green" | "amber" | "red" | "slate" | "sky" {
  if (s === "registered") return "green";
  if (s === "invite_pending") return "amber";
  return "slate";
}

function labelFor(value: string, options: readonly { value: string; label: string }[]) {
  return options.find((o) => o.value === value)?.label ?? value.replace(/_/g, " ");
}

export function UsersPanel({ onRefetch }: { onRefetch: () => void }) {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const [tab, setTab] = useState<UserDirectoryTab>("staff");
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");

  return (
    <div className="space-y-6">
      <SettingsPageHeader title="Users" description={SECTION_DESCRIPTIONS.users} />

      <div className="rounded-xl border border-amber-200/80 bg-amber-50/80 px-4 py-3 text-sm text-amber-950">
        <strong>Clerk manages passwords.</strong> Porterchain never stores or displays passwords.
        You can set a password when creating a user or reset it here — Clerk holds credentials; this
        screen shows <em>password set / not set</em> and live Clerk status (banned, locked, last
        sign-in).
      </div>

      <div className="flex flex-wrap gap-2 border-b border-primary/10 pb-1">
        {USER_TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={cn(
              "inline-flex items-center gap-2 rounded-t-lg px-4 py-2.5 text-sm font-semibold transition-colors",
              tab === id
                ? "border-b-2 border-secondary bg-secondary/5 text-secondary"
                : "text-muted hover:bg-gray-bg/60 hover:text-primary"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "staff" ? (
        <StaffTab enabled={enabled} getApiToken={getApiToken} onRefetch={onRefetch} />
      ) : (
        <DirectoryTab tab={tab} enabled={enabled} getApiToken={getApiToken} />
      )}
    </div>
  );
}

function UserFiltersBar({
  filters,
  facets,
  showAccountFilter,
  onChange,
  onClear,
}: {
  filters: UserDirectoryFilters;
  facets?: PlatformUsersFacets;
  showAccountFilter?: boolean;
  onChange: (next: UserDirectoryFilters) => void;
  onClear: () => void;
}) {
  const accountOptions = useMemo(() => {
    const keys = Object.keys(facets?.account_status ?? {}).sort();
    return [
      { value: "", label: "All account statuses" },
      ...keys.map((k) => ({ value: k, label: k.replace(/_/g, " ") })),
    ];
  }, [facets]);

  const hasFilters = Boolean(
    filters.search ||
    filters.access_status ||
    filters.invite_status ||
    filters.identity_status ||
    filters.account_status ||
    filters.clerk_status
  );

  return (
    <div className="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-primary/10 bg-gray-bg/30 p-3">
      <Field label="Search" className="min-w-[12rem] flex-1">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input
            className="pl-9"
            placeholder="Email, name, organization…"
            value={filters.search ?? ""}
            onChange={(e) => onChange({ ...filters, search: e.target.value || undefined })}
          />
        </div>
      </Field>
      <Field label="Access" className="min-w-[9rem]">
        <Select
          value={filters.access_status ?? ""}
          onChange={(e) => onChange({ ...filters, access_status: e.target.value || undefined })}
        >
          {ACCESS_STATUS_OPTIONS.map((o) => (
            <option key={o.value || "all"} value={o.value}>
              {o.label}
              {o.value && facets?.access_status?.[o.value] != null
                ? ` (${facets.access_status[o.value]})`
                : ""}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Invitation" className="min-w-[9rem]">
        <Select
          value={filters.invite_status ?? ""}
          onChange={(e) => onChange({ ...filters, invite_status: e.target.value || undefined })}
        >
          {INVITE_STATUS_OPTIONS.map((o) => (
            <option key={o.value || "all"} value={o.value}>
              {o.label}
              {o.value && facets?.invite_status?.[o.value] != null
                ? ` (${facets.invite_status[o.value]})`
                : ""}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Clerk identity" className="min-w-[9rem]">
        <Select
          value={filters.identity_status ?? ""}
          onChange={(e) => onChange({ ...filters, identity_status: e.target.value || undefined })}
        >
          {IDENTITY_STATUS_OPTIONS.map((o) => (
            <option key={o.value || "all"} value={o.value}>
              {o.label}
              {o.value && facets?.identity_status?.[o.value] != null
                ? ` (${facets.identity_status[o.value]})`
                : ""}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Clerk status" className="min-w-[9rem]">
        <Select
          value={filters.clerk_status ?? ""}
          onChange={(e) => onChange({ ...filters, clerk_status: e.target.value || undefined })}
        >
          {CLERK_STATUS_OPTIONS.map((o) => (
            <option key={o.value || "all"} value={o.value}>
              {o.label}
              {o.value && facets?.clerk_status?.[o.value] != null
                ? ` (${facets.clerk_status[o.value]})`
                : ""}
            </option>
          ))}
        </Select>
      </Field>
      {showAccountFilter && (
        <Field label="Account" className="min-w-[9rem]">
          <Select
            value={filters.account_status ?? ""}
            onChange={(e) => onChange({ ...filters, account_status: e.target.value || undefined })}
          >
            {accountOptions.map((o) => (
              <option key={o.value || "all"} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </Field>
      )}
      {hasFilters && (
        <Button variant="ghost" onClick={onClear} className="mb-0.5">
          <X className="h-4 w-4" /> Clear
        </Button>
      )}
    </div>
  );
}

function useUserDirectory(
  tab: UserDirectoryTab,
  filters: UserDirectoryFilters,
  enabled: boolean,
  getApiToken: () => Promise<string | null>
) {
  return useQuery({
    queryKey: ["settings-users", tab, filters],
    enabled,
    queryFn: async () => settingsApi.users(await requireApiToken(getApiToken), tab, filters),
  });
}

function DirectoryTab({
  tab,
  enabled,
  getApiToken,
}: {
  tab: Exclude<UserDirectoryTab, "staff">;
  enabled: boolean;
  getApiToken: () => Promise<string | null>;
}) {
  const qc = useQueryClient();
  const [filters, setFilters] = useState<UserDirectoryFilters>(EMPTY_FILTERS);
  const [createOpen, setCreateOpen] = useState(false);
  const meta = USER_TABS.find((t) => t.id === tab)!;
  const { data, isLoading } = useUserDirectory(tab, filters, enabled, getApiToken);
  const users = data?.items ?? [];
  const facets = data?.facets;

  const refresh = () => void qc.invalidateQueries({ queryKey: ["settings-users", tab] });

  return (
    <SettingsCard
      title={meta.label}
      description={meta.description}
      action={
        <Button onClick={() => setCreateOpen(true)}>
          <UserPlus className="h-4 w-4" /> Add user
        </Button>
      }
    >
      <UserFiltersBar
        filters={filters}
        facets={facets}
        showAccountFilter={tab === "driver"}
        onChange={setFilters}
        onClear={() => setFilters(EMPTY_FILTERS)}
      />
      {isLoading ? (
        <Spinner />
      ) : (
        <>
          <p className="mb-3 text-xs text-muted">
            Showing {data?.total ?? 0} user{(data?.total ?? 0) === 1 ? "" : "s"}
            {data?.clerk_synced
              ? ` · ${data.clerk_total ?? 0} in Clerk`
              : " · Clerk sync unavailable"}
          </p>
          <UserDirectoryTable
            users={users}
            tab={tab}
            getApiToken={getApiToken}
            showOrganization={tab === "merchant"}
            onMutate={refresh}
          />
        </>
      )}
      <CreateUserModal
        open={createOpen}
        tab={tab}
        getApiToken={getApiToken}
        onClose={() => setCreateOpen(false)}
        onCreated={refresh}
      />
    </SettingsCard>
  );
}

function StaffTab({
  enabled,
  getApiToken,
  onRefetch,
}: {
  enabled: boolean;
  getApiToken: () => Promise<string | null>;
  onRefetch: () => void;
}) {
  const qc = useQueryClient();
  const [filters, setFilters] = useState<UserDirectoryFilters>(EMPTY_FILTERS);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [roleModal, setRoleModal] = useState<StaffUser | null>(null);
  const [inviteForm, setInviteForm] = useState({ email: "", role: "dispatcher", name: "" });
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviting, setInviting] = useState(false);

  const { data, isLoading } = useUserDirectory("staff", filters, enabled, getApiToken);
  const users = data?.items ?? [];
  const facets = data?.facets;

  async function submitInvite() {
    setInviting(true);
    setInviteError(null);
    try {
      await settingsApi.inviteStaff(await requireApiToken(getApiToken), {
        email: inviteForm.email.trim(),
        role: inviteForm.role,
        name: inviteForm.name.trim() || undefined,
      });
      setInviteOpen(false);
      setInviteForm({ email: "", role: "dispatcher", name: "" });
      void qc.invalidateQueries({ queryKey: ["settings-users", "staff"] });
      onRefetch();
    } catch (e) {
      setInviteError(e instanceof Error ? e.message : "Invite failed");
    } finally {
      setInviting(false);
    }
  }

  return (
    <>
      <SettingsCard
        title="Staff"
        description="All provisioned admin users — invitation and Clerk status shown even when not yet authorized"
        action={
          <Button onClick={() => setInviteOpen(true)}>
            <UserPlus className="h-4 w-4" /> Invite staff
          </Button>
        }
      >
        <UserFiltersBar
          filters={filters}
          facets={facets}
          onChange={setFilters}
          onClear={() => setFilters(EMPTY_FILTERS)}
        />
        {isLoading ? (
          <Spinner />
        ) : (
          <>
            <p className="mb-3 text-xs text-muted">
              Showing {data?.total ?? 0} staff member{(data?.total ?? 0) === 1 ? "" : "s"}
            </p>
            <UserDirectoryTable
              users={users}
              tab="staff"
              getApiToken={getApiToken}
              onMutate={() => void qc.invalidateQueries({ queryKey: ["settings-users", "staff"] })}
              staffActions={(user) => (
                <Button variant="outline" onClick={() => setRoleModal(staffFromPlatform(user))}>
                  Change role
                </Button>
              )}
            />
          </>
        )}
      </SettingsCard>

      <Modal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        title="Invite staff member"
        footer={
          <>
            <Button variant="outline" onClick={() => setInviteOpen(false)}>
              Cancel
            </Button>
            <Button disabled={!inviteForm.email || inviting} onClick={() => void submitInvite()}>
              {inviting ? "Sending…" : "Send invitation"}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Work email">
            <Input
              type="email"
              placeholder="name@porterchain.com"
              value={inviteForm.email}
              onChange={(e) => setInviteForm((f) => ({ ...f, email: e.target.value }))}
            />
          </Field>
          <Field label="Display name">
            <Input
              value={inviteForm.name}
              onChange={(e) => setInviteForm((f) => ({ ...f, name: e.target.value }))}
            />
          </Field>
          <Field label="Role">
            <Select
              value={inviteForm.role}
              onChange={(e) => setInviteForm((f) => ({ ...f, role: e.target.value }))}
            >
              {ADMIN_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
          </Field>
          {inviteError && <p className="text-sm text-red-600">{inviteError}</p>}
        </div>
      </Modal>

      {roleModal && (
        <ChangeRoleModal user={roleModal} onClose={() => setRoleModal(null)} onSaved={onRefetch} />
      )}
    </>
  );
}

function staffFromPlatform(user: PlatformUser): StaffUser {
  return {
    id: user.id,
    email: user.email,
    name: user.name,
    role: user.role ?? "read_only",
    created_at: user.created_at,
  };
}

function UserDirectoryTable({
  users,
  tab,
  getApiToken,
  showOrganization = false,
  staffActions,
  onMutate,
}: {
  users: PlatformUser[];
  tab: UserDirectoryTab;
  getApiToken: () => Promise<string | null>;
  showOrganization?: boolean;
  staffActions?: (user: PlatformUser) => ReactNode;
  onMutate: () => void;
}) {
  const [manageUser, setManageUser] = useState<PlatformUser | null>(null);

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-primary/10 text-left text-xs uppercase tracking-wide text-muted">
              <th className="pb-3 pr-4 font-semibold">User</th>
              <th className="pb-3 pr-4 font-semibold">Role</th>
              <th className="pb-3 pr-4 font-semibold">Access</th>
              <th className="pb-3 pr-4 font-semibold">Invitation</th>
              <th className="pb-3 pr-4 font-semibold">Clerk</th>
              <th className="pb-3 pr-4 font-semibold">Password</th>
              {showOrganization && <th className="pb-3 pr-4 font-semibold">Organization</th>}
              <th className="pb-3 pr-4 font-semibold">Added</th>
              <th className="pb-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-primary/5">
            {users.map((u) => (
              <tr key={`${u.user_type}-${u.id}`} className="group">
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-3">
                    <Avatar name={u.name ?? u.email} />
                    <div className="min-w-0">
                      <p className="font-medium text-primary">
                        {u.name || u.email.split("@")[0]}
                        {!u.provisioned && (
                          <span className="ml-2 text-[10px] font-semibold uppercase text-amber-700">
                            Clerk only
                          </span>
                        )}
                      </p>
                      <p className="flex items-center gap-1 truncate text-xs text-muted">
                        <Mail className="h-3 w-3 shrink-0" />
                        {u.email}
                      </p>
                      <p className="mt-0.5 text-[11px] leading-snug text-muted">{u.status_label}</p>
                    </div>
                  </div>
                </td>
                <td className="py-3 pr-4">
                  <Badge tone="sky">{(u.role ?? u.user_type).replace(/_/g, " ")}</Badge>
                  {u.status && u.user_type === "driver" && (
                    <p className="mt-1 text-[11px] text-muted">{u.status}</p>
                  )}
                </td>
                <td className="py-3 pr-4">
                  <Badge tone={accessTone(u.access_status)}>
                    {labelFor(u.access_status, ACCESS_STATUS_OPTIONS)}
                  </Badge>
                </td>
                <td className="py-3 pr-4">
                  <Badge tone={inviteTone(u.invite_status)}>
                    {labelFor(u.invite_status, INVITE_STATUS_OPTIONS)}
                  </Badge>
                </td>
                <td className="py-3 pr-4">
                  <Badge tone={identityTone(u.identity_status)}>
                    {u.clerk_status
                      ? labelFor(u.clerk_status, CLERK_STATUS_OPTIONS)
                      : labelFor(u.identity_status, IDENTITY_STATUS_OPTIONS)}
                  </Badge>
                </td>
                <td className="py-3 pr-4">
                  <Badge tone={u.clerk_password_set ? "green" : "slate"}>
                    {u.clerk_user_id ? (u.clerk_password_set ? "Set" : "Not set") : "—"}
                  </Badge>
                </td>
                {showOrganization && (
                  <td className="py-3 pr-4 text-muted">{u.organization ?? "—"}</td>
                )}
                <td className="py-3 pr-4 text-muted">{shortDate(u.created_at)}</td>
                <td className="py-3">
                  <div className="flex flex-wrap gap-2">
                    {staffActions?.(u)}
                    {u.clerk_user_id && (
                      <Button variant="outline" onClick={() => setManageUser(u)}>
                        Manage
                      </Button>
                    )}
                    {u.detail_href && (
                      <Link
                        href={u.detail_href}
                        className="inline-flex items-center rounded-lg border border-primary/15 px-3 py-1.5 text-xs font-semibold text-primary hover:bg-secondary/5"
                      >
                        Open
                      </Link>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!users.length && (
          <p className="py-8 text-center text-sm text-muted">No users match the current filters.</p>
        )}
      </div>
      {manageUser?.clerk_user_id && (
        <ManageClerkUserModal
          user={manageUser}
          tab={tab}
          getApiToken={getApiToken}
          onClose={() => setManageUser(null)}
          onSaved={onMutate}
        />
      )}
    </>
  );
}

function CreateUserModal({
  open,
  tab,
  getApiToken,
  onClose,
  onCreated,
}: {
  open: boolean;
  tab: UserDirectoryTab;
  getApiToken: () => Promise<string | null>;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState(tab === "staff" ? "dispatcher" : "driver");
  const [password, setPassword] = useState("");
  const [sendInvite, setSendInvite] = useState(true);
  const [merchantId, setMerchantId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await settingsApi.createUser(await requireApiToken(getApiToken), tab, {
        email: email.trim(),
        name: name.trim() || undefined,
        role: tab === "staff" || tab === "merchant" ? role : undefined,
        password: password.trim() || undefined,
        send_invite: sendInvite && !password.trim(),
        merchant_id: tab === "merchant" ? merchantId.trim() || undefined : undefined,
      });
      onCreated();
      onClose();
      setEmail("");
      setName("");
      setPassword("");
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
      title={`Add ${tab} user`}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={!email.trim() || busy} onClick={() => void submit()}>
            {busy ? "Saving…" : "Create"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Email">
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Name">
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        {tab === "staff" && (
          <Field label="Role">
            <Select value={role} onChange={(e) => setRole(e.target.value)}>
              {ADMIN_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
          </Field>
        )}
        {tab === "merchant" && (
          <>
            <Field label="Merchant ID">
              <Input
                value={merchantId}
                onChange={(e) => setMerchantId(e.target.value)}
                placeholder="UUID"
              />
            </Field>
            <Field label="Merchant role">
              <Input
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="merchant_ops"
              />
            </Field>
          </>
        )}
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
            Send Clerk invitation email
          </label>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </Modal>
  );
}

const AUTHORIZE_COPY: Record<UserDirectoryTab, { title: string; detail: string; role: string }> = {
  staff: {
    title: "Authorize all admin modules",
    detail: "Promotes to super_admin and activates staff access for every admin portal module.",
    role: "super_admin",
  },
  merchant: {
    title: "Authorize all merchant modules",
    detail: "Sets merchant_owner, activates the user, and approves the merchant organization.",
    role: "merchant_owner",
  },
  driver: {
    title: "Authorize driver portal",
    detail: "Approves the driver for full driver portal and mobile access.",
    role: "approved",
  },
  customer: {
    title: "Authorize customer portal",
    detail: "Ensures the customer record is linked and active for quote, book, and order flows.",
    role: "customer",
  },
};

function ManageClerkUserModal({
  user,
  tab,
  getApiToken,
  onClose,
  onSaved,
}: {
  user: PlatformUser;
  tab: UserDirectoryTab;
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

  const authorizeCopy = AUTHORIZE_COPY[tab];
  const canAuthorize = user.access_status !== "authorized" || !user.provisioned;

  async function authorizeAllModules() {
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
      const result = await settingsApi.authorizeUser(await requireApiToken(getApiToken), tab, {
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
      await settingsApi.updateClerkUser(await requireApiToken(getApiToken), tab, {
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
      await settingsApi.deleteUser(await requireApiToken(getApiToken), tab, {
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
      title={`Manage — ${user.email}`}
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
          <Badge tone={accessTone(user.access_status)}>
            {labelFor(user.access_status, ACCESS_STATUS_OPTIONS)}
          </Badge>
          {!user.provisioned && <Badge tone="amber">Not provisioned in Porterchain</Badge>}
        </div>

        <div className="rounded-xl border border-secondary/20 bg-secondary/5 p-4">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-secondary" />
            <div className="min-w-0 flex-1 space-y-3">
              <div>
                <p className="font-semibold text-primary">{authorizeCopy.title}</p>
                <p className="mt-1 text-muted">{authorizeCopy.detail}</p>
                <p className="mt-2 text-xs text-muted">
                  Target role: <code className="rounded bg-white px-1">{authorizeCopy.role}</code>
                </p>
              </div>
              <Button variant="outline" disabled={busy} onClick={() => void authorizeAllModules()}>
                {busy ? "Authorizing…" : canAuthorize ? "Authorize user" : "Re-check authorization"}
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

function ChangeRoleModal({
  user,
  onClose,
  onSaved,
}: {
  user: StaffUser;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const qc = useQueryClient();
  const [role, setRole] = useState(user.role);
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await settingsApi.updateStaffRole(await getApiToken(), user.id, role, reason || undefined);
      void qc.invalidateQueries({ queryKey: ["settings-users", "staff"] });
      onSaved();
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Change role — ${user.email}`}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={saving} onClick={() => void save()}>
            {saving ? "Saving…" : "Update role"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="New role">
          <Select value={role} onChange={(e) => setRole(e.target.value)}>
            {ADMIN_ROLES.map((r) => (
              <option key={r} value={r}>
                {r.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Reason (audit)">
          <Input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Optional"
          />
        </Field>
      </div>
    </Modal>
  );
}

export function RolesPanel({
  permissions,
  roles,
}: {
  permissions: Record<string, string[]>;
  roles: string[];
}) {
  const [view, setView] = useState<"modules" | "roles">("modules");

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title="Roles & permissions"
        description={SECTION_DESCRIPTIONS.roles}
        actions={
          <div className="flex rounded-xl border border-primary/10 p-0.5">
            {(["modules", "roles"] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setView(v)}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-xs font-semibold capitalize",
                  view === v ? "bg-secondary text-white" : "text-muted hover:text-primary"
                )}
              >
                By {v}
              </button>
            ))}
          </div>
        }
      />

      <SettingsCard
        title="Enterprise RBAC"
        description="Porterchain owns authorization — Clerk Organizations are never used for access control"
      >
        <div className="mb-4 flex flex-wrap gap-2">
          {roles.map((r) => (
            <Badge key={r} tone="violet">
              {r.replace(/_/g, " ")}
            </Badge>
          ))}
        </div>

        {view === "modules" ? (
          <div className="max-h-[28rem] overflow-auto rounded-xl border border-primary/10">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-gray-bg">
                <tr className="border-b border-primary/10 text-left">
                  <th className="px-3 py-2 font-semibold text-primary">Admin module</th>
                  <th className="px-3 py-2 font-semibold text-primary">Allowed roles</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(permissions).map(([mod, allowed]) => (
                  <tr key={mod} className="border-b border-primary/5 hover:bg-secondary/5">
                    <td className="px-3 py-2.5 font-mono font-medium text-primary">{mod}</td>
                    <td className="px-3 py-2.5 text-muted">{allowed.join(" · ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-muted">
            {roles.length} enterprise roles mapped from admin_users.role and merchant_users.role.
            Full matrix available via{" "}
            <code className="rounded bg-gray-bg px-1">GET /v1/auth/rbac</code>.
          </p>
        )}
      </SettingsCard>

      <div className="flex items-start gap-3 rounded-xl border border-secondary/20 bg-secondary/5 p-4 text-sm">
        <Shield className="mt-0.5 h-5 w-5 shrink-0 text-secondary" />
        <p className="text-primary/80">
          Every protected API route calls{" "}
          <code className="rounded bg-white px-1">require_module()</code> server-side. Portal UI
          gates are defense in depth only.
        </p>
      </div>
    </div>
  );
}

export const StaffPanel = UsersPanel;
