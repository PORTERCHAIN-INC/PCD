"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Shield } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { SECTION_DESCRIPTIONS } from "@/lib/settings-metadata";
import { settingsApi, type RoleCatalogEntry } from "@/lib/settings";
import { SettingsCard, SettingsPageHeader } from "../ui/SettingsPrimitives";

export function RolesPanel() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const { data: center, isLoading } = useQuery({
    queryKey: ["admin", "settings", "center", "roles"],
    enabled: isLoaded && isSignedIn,
    queryFn: async () => settingsApi.center(await getApiToken()),
  });

  const roles = (center?.role_catalog?.roles ?? center?.roles ?? []) as RoleCatalogEntry[];
  const modules = useMemo(() => {
    if (center?.role_catalog?.modules?.length) {
      return center.role_catalog.modules.map((m) => m.module);
    }
    return Object.keys(center?.permissions ?? {}).sort();
  }, [center]);

  const allowed = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const role of roles) {
      map.set(role.role, new Set(role.modules));
    }
    return map;
  }, [roles]);

  return (
    <div className="space-y-6">
      <SettingsPageHeader title="Roles & permissions" description={SECTION_DESCRIPTIONS.roles} />

      <SettingsCard
        title="Staff role → module catalog"
        description="Read-only matrix from MODULE_PERMISSIONS. Change access by updating a staff member’s role on the Users tab — not by editing this grid."
      >
        {isLoading && <p className="text-sm text-muted">Loading catalog…</p>}
        {!isLoading && roles.length === 0 && (
          <p className="text-sm text-muted">Role catalog unavailable.</p>
        )}
        {roles.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-primary/10">
                  <th className="sticky left-0 z-10 bg-white px-2 py-2 font-semibold text-primary">
                    Module
                  </th>
                  {roles.map((role) => (
                    <th
                      key={role.role}
                      className="px-2 py-2 font-semibold text-primary whitespace-nowrap"
                      title={role.role}
                    >
                      {role.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {modules.map((module) => (
                  <tr key={module} className="border-b border-primary/5">
                    <td className="sticky left-0 z-10 bg-white px-2 py-1.5 font-mono text-[11px] text-primary/80">
                      {module}
                    </td>
                    {roles.map((role) => {
                      const ok = allowed.get(role.role)?.has(module);
                      return (
                        <td key={`${module}-${role.role}`} className="px-2 py-1.5 text-center">
                          {ok ? (
                            <Check
                              className="mx-auto h-3.5 w-3.5 text-secondary"
                              aria-label="allowed"
                            />
                          ) : (
                            <span className="text-primary/15">·</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SettingsCard>

      <SettingsCard
        title="SpiceDB authorization"
        description="Clerk authenticates retail portals. Staff use PorterChain IdP. SpiceDB authorizes every Check."
      >
        <p className="text-sm text-muted">
          Live rules are in <code className="rounded bg-gray-bg px-1">authz/schema.zed</code>
          {center?.authz?.schema ? (
            <>
              {" "}
              (<code className="rounded bg-gray-bg px-1">{center.authz.schema}</code>)
            </>
          ) : null}
          . Session permissions come from{" "}
          <code className="rounded bg-gray-bg px-1">GET /v1/auth/session-context</code>. The matrix
          above is a UX catalog only — Checks never fall back to it.
        </p>
      </SettingsCard>

      <div className="flex items-start gap-3 rounded-xl border border-secondary/20 bg-secondary/5 p-4 text-sm">
        <Shield className="mt-0.5 h-5 w-5 shrink-0 text-secondary" />
        <p className="text-primary/80">
          Protected routes call SpiceDB Check (via{" "}
          <code className="rounded bg-white px-1">require_relation</code> /{" "}
          <code className="rounded bg-white px-1">require_module</code>). Portal UI gates are
          defense in depth only.
        </p>
      </div>
    </div>
  );
}
