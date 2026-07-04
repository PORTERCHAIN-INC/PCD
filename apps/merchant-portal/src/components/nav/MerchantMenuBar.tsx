"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronDown, LayoutGrid } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  ALL_MERCHANT_NAV_ITEMS,
  MERCHANT_NAV_GROUPS,
  isNavActive,
  type MerchantNavItem,
} from "@/lib/merchant-nav";
import NavDropdown from "@/components/nav/NavDropdown";

function NavLinkItem({
  href,
  label,
  description,
  icon: Icon,
  pathname,
  onNavigate,
}: MerchantNavItem & { pathname: string; onNavigate?: () => void }) {
  const active = isNavActive(pathname, href);
  return (
    <Link
      href={href}
      onClick={onNavigate}
      role="menuitem"
      className={cn(
        "flex items-start gap-3 rounded-lg px-3 py-2.5 transition",
        active ? "bg-secondary/10" : "hover:bg-gray-bg"
      )}
    >
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", active ? "text-secondary" : "text-muted")} />
      <span className="min-w-0">
        <span
          className={cn("block text-sm font-medium", active ? "text-secondary" : "text-primary")}
        >
          {label}
        </span>
        {description && <span className="block text-xs text-muted">{description}</span>}
      </span>
    </Link>
  );
}

function AllModulesPanel({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <div className="max-h-[min(70dvh,520px)] overflow-y-auto p-2">
      <p className="px-3 py-2 text-xs font-semibold text-muted">All merchant modules</p>
      <div className="grid gap-1 sm:grid-cols-2">
        {ALL_MERCHANT_NAV_ITEMS.map((item) => (
          <NavLinkItem key={item.href} {...item} pathname={pathname} onNavigate={onNavigate} />
        ))}
      </div>
    </div>
  );
}

function GroupPanel({
  groupLabel,
  items,
  pathname,
  onNavigate,
}: {
  groupLabel: string;
  items: MerchantNavItem[];
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <div className="p-1.5">
      <p className="px-3 pb-1 pt-2 text-[10px] font-bold uppercase tracking-wider text-muted">
        {groupLabel}
      </p>
      {items.map((item) => (
        <NavLinkItem key={item.href} {...item} pathname={pathname} onNavigate={onNavigate} />
      ))}
    </div>
  );
}

export default function MerchantMenuBar() {
  const pathname = usePathname();

  return (
    <nav className="flex min-w-0 flex-1 flex-wrap items-center gap-1" aria-label="Main menu">
      <NavDropdown
        width="xl"
        trigger={({ open, triggerProps }) => (
          <button
            type="button"
            {...triggerProps}
            className={cn(
              "flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-sm font-medium whitespace-nowrap transition",
              open ? "bg-secondary/10 text-secondary" : "text-primary/80 hover:bg-primary/5"
            )}
          >
            <LayoutGrid className="h-4 w-4" />
            All modules
            <ChevronDown
              className={cn("h-3.5 w-3.5 opacity-60 transition", open && "rotate-180")}
            />
          </button>
        )}
      >
        <AllModulesPanel pathname={pathname} />
      </NavDropdown>

      <span className="mx-0.5 hidden h-5 w-px bg-primary/10 md:inline" />

      {MERCHANT_NAV_GROUPS.map((group) => {
        const active = group.items.some((item) => isNavActive(pathname, item.href));
        const single = group.items.length === 1;

        if (single) {
          const item = group.items[0]!;
          return (
            <Link
              key={group.id}
              href={item.href}
              className={cn(
                "hidden shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium whitespace-nowrap transition md:inline-flex",
                isNavActive(pathname, item.href)
                  ? "bg-secondary/10 text-secondary"
                  : "text-primary/80 hover:bg-primary/5"
              )}
            >
              {group.label}
            </Link>
          );
        }

        return (
          <NavDropdown
            key={group.id}
            width="md"
            trigger={({ open, triggerProps }) => (
              <button
                type="button"
                {...triggerProps}
                className={cn(
                  "hidden items-center gap-1 rounded-lg px-3 py-1.5 text-sm font-medium whitespace-nowrap transition md:inline-flex",
                  active || open
                    ? "bg-secondary/10 text-secondary"
                    : "text-primary/80 hover:bg-primary/5"
                )}
              >
                {group.label}
                <ChevronDown
                  className={cn("h-3.5 w-3.5 opacity-60 transition", open && "rotate-180")}
                />
              </button>
            )}
          >
            <GroupPanel groupLabel={group.label} items={group.items} pathname={pathname} />
          </NavDropdown>
        );
      })}
    </nav>
  );
}
