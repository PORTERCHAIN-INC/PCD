"use client";

import { useOrganizationList } from "@clerk/nextjs";
import { Building2 } from "lucide-react";
import { cn } from "@/lib/utils";

type Props = {
  className?: string;
  onSelected?: () => void;
};

/** Porterchain-styled org picker — no Clerk "Secured by" branding. */
export default function MerchantOrgPicker({ className, onSelected }: Props) {
  const { isLoaded, userMemberships, setActive } = useOrganizationList({
    userMemberships: { infinite: true },
  });

  if (!isLoaded) {
    return <p className="text-sm text-muted">Loading organizations…</p>;
  }

  const memberships = userMemberships.data ?? [];
  if (memberships.length === 0) {
    return <p className="text-sm text-muted">No business organizations on this account.</p>;
  }

  return (
    <ul className={cn("space-y-1", className)}>
      {memberships.map((mem) => {
        const org = mem.organization;
        if (!org) return null;
        return (
          <li key={org.id}>
            <button
              type="button"
              onClick={() => {
                void setActive({ organization: org.id }).then(() => onSelected?.());
              }}
              className="flex w-full items-center gap-3 rounded-xl border border-primary/10 px-3 py-2.5 text-left transition hover:bg-gray-bg"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-secondary/10">
                <Building2 className="h-4 w-4 text-secondary" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-primary">{org.name}</span>
                <span className="block text-xs text-muted">Business account</span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
