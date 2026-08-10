"use client";

import { useMemo } from "react";
import { Search, X } from "lucide-react";
import { Button, Field, Input, Select } from "@/components/crm/primitives";
import {
  ACCESS_STATUS_OPTIONS,
  CLERK_STATUS_OPTIONS,
  IDENTITY_STATUS_OPTIONS,
  INVITE_STATUS_OPTIONS,
  type PlatformUsersFacets,
  type UserDirectoryFilters,
  type UserDirectoryTab,
} from "@/lib/settings";

const EMPTY_FILTERS: UserDirectoryFilters = {};

export { EMPTY_FILTERS };

/** Filter chrome keyed to persona — Clerk invite facets only for drivers. */
export function filterChromeFor(tab: UserDirectoryTab) {
  return {
    showInviteFilter: tab === "driver",
    showClerkFilters: tab === "driver",
    showAccountFilter: tab === "driver",
  };
}

export function UserFiltersBar({
  filters,
  facets,
  showAccountFilter,
  showInviteFilter = true,
  showClerkFilters = true,
  onChange,
  onClear,
}: {
  filters: UserDirectoryFilters;
  facets?: PlatformUsersFacets;
  showAccountFilter?: boolean;
  showInviteFilter?: boolean;
  showClerkFilters?: boolean;
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
      {showInviteFilter && (
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
      )}
      {showClerkFilters && (
        <>
          <Field label="Clerk identity" className="min-w-[9rem]">
            <Select
              value={filters.identity_status ?? ""}
              onChange={(e) =>
                onChange({ ...filters, identity_status: e.target.value || undefined })
              }
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
        </>
      )}
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
