"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type { UserDirectoryTab } from "@/lib/settings";
import { SECTION_DESCRIPTIONS } from "@/lib/settings-metadata";
import { SettingsPageHeader } from "../../ui/SettingsPrimitives";
import { USER_TABS } from "./constants";
import { DirectoryShell } from "./DirectoryShell";

const TAB_IDS = new Set(USER_TABS.map((t) => t.id));

function resolveUserTab(raw: string | null): UserDirectoryTab {
  if (raw && TAB_IDS.has(raw as UserDirectoryTab)) return raw as UserDirectoryTab;
  return "staff";
}

export function UsersPanel({ onRefetch }: { onRefetch: () => void }) {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [tab, setTab] = useState<UserDirectoryTab>(() => resolveUserTab(searchParams.get("tab")));
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");

  useEffect(() => {
    setTab(resolveUserTab(searchParams.get("tab")));
  }, [searchParams]);

  function selectTab(next: UserDirectoryTab) {
    setTab(next);
    const params = new URLSearchParams(searchParams.toString());
    params.set("section", "users");
    params.set("tab", next);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }

  return (
    <div className="space-y-6">
      <SettingsPageHeader title="Users" description={SECTION_DESCRIPTIONS.users} />

      <div className="rounded-xl border border-amber-200/80 bg-amber-50/80 px-4 py-3 text-sm text-amber-950">
        <strong>Auth by persona:</strong> Staff use staff IdP enroll (+ activate link). Drivers use
        Clerk invites. Merchants get email seats (self SignUp). Customers self SignUp only. Open a
        row’s Partners profile via <strong>Open</strong> when listed.
      </div>

      <div className="flex flex-wrap gap-2 border-b border-primary/10 pb-1">
        {USER_TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => selectTab(id)}
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

      <DirectoryShell
        key={tab}
        tab={tab}
        enabled={enabled}
        getApiToken={getApiToken}
        onRefetch={onRefetch}
      />
    </div>
  );
}
