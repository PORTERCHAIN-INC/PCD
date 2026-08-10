"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { Mail } from "lucide-react";
import { Avatar, Badge, Button } from "@/components/crm/primitives";
import { shortDate } from "@/lib/crmFormat";
import type { PlatformUser, UserDirectoryTab } from "@/lib/settings";
import { DIRECTORY_COLUMNS, type DirectoryColumn } from "./constants";
import { ManageDriverModal } from "./driver/ManageDriverModal";
import {
  accessLabel,
  accessTone,
  clerkLabel,
  identityTone,
  inviteLabel,
  inviteTone,
} from "./status";

function hasCol(cols: DirectoryColumn[], key: DirectoryColumn) {
  return cols.includes(key);
}

export function UserDirectoryTable({
  users,
  tab,
  getApiToken,
  rowActions,
  onMutate,
}: {
  users: PlatformUser[];
  tab: UserDirectoryTab;
  getApiToken: () => Promise<string | null>;
  rowActions?: (user: PlatformUser) => ReactNode;
  onMutate: () => void;
}) {
  const cols = DIRECTORY_COLUMNS[tab];
  const [manageUser, setManageUser] = useState<PlatformUser | null>(null);

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-primary/10 text-left text-xs uppercase tracking-wide text-muted">
              <th className="pb-3 pr-4 font-semibold">User</th>
              {hasCol(cols, "role") && <th className="pb-3 pr-4 font-semibold">Role</th>}
              {hasCol(cols, "access") && <th className="pb-3 pr-4 font-semibold">Access</th>}
              {hasCol(cols, "invitation") && (
                <th className="pb-3 pr-4 font-semibold">Invitation</th>
              )}
              {hasCol(cols, "clerk") && <th className="pb-3 pr-4 font-semibold">Clerk</th>}
              {hasCol(cols, "password") && <th className="pb-3 pr-4 font-semibold">Password</th>}
              {hasCol(cols, "organization") && (
                <th className="pb-3 pr-4 font-semibold">Organization</th>
              )}
              {hasCol(cols, "added") && <th className="pb-3 pr-4 font-semibold">Added</th>}
              {hasCol(cols, "actions") && <th className="pb-3 font-semibold">Actions</th>}
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
                {hasCol(cols, "role") && (
                  <td className="py-3 pr-4">
                    <Badge tone="sky">{(u.role ?? u.user_type).replace(/_/g, " ")}</Badge>
                    {u.status && u.user_type === "driver" && (
                      <p className="mt-1 text-[11px] text-muted">{u.status}</p>
                    )}
                  </td>
                )}
                {hasCol(cols, "access") && (
                  <td className="py-3 pr-4">
                    <Badge tone={accessTone(u.access_status)}>{accessLabel(u.access_status)}</Badge>
                  </td>
                )}
                {hasCol(cols, "invitation") && (
                  <td className="py-3 pr-4">
                    <Badge tone={inviteTone(u.invite_status)}>{inviteLabel(u.invite_status)}</Badge>
                  </td>
                )}
                {hasCol(cols, "clerk") && (
                  <td className="py-3 pr-4">
                    <Badge tone={identityTone(u.identity_status)}>
                      {clerkLabel(u.clerk_status, u.identity_status)}
                    </Badge>
                  </td>
                )}
                {hasCol(cols, "password") && (
                  <td className="py-3 pr-4">
                    <Badge tone={u.clerk_password_set ? "green" : "slate"}>
                      {u.clerk_user_id ? (u.clerk_password_set ? "Set" : "Not set") : "—"}
                    </Badge>
                  </td>
                )}
                {hasCol(cols, "organization") && (
                  <td className="py-3 pr-4 text-muted">{u.organization ?? "—"}</td>
                )}
                {hasCol(cols, "added") && (
                  <td className="py-3 pr-4 text-muted">{shortDate(u.created_at)}</td>
                )}
                {hasCol(cols, "actions") && (
                  <td className="py-3">
                    <div className="flex flex-wrap gap-2">
                      {rowActions?.(u)}
                      {tab === "driver" && u.clerk_user_id && (
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
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {!users.length && (
          <p className="py-8 text-center text-sm text-muted">No users match the current filters.</p>
        )}
      </div>
      {tab === "driver" && manageUser?.clerk_user_id && (
        <ManageDriverModal
          user={manageUser}
          getApiToken={getApiToken}
          onClose={() => setManageUser(null)}
          onSaved={onMutate}
        />
      )}
    </>
  );
}
