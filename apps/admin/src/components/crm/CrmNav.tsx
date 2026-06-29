"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Building2,
  CalendarDays,
  ClipboardList,
  Contact,
  FileText,
  LayoutDashboard,
  ScrollText,
  Target,
  Upload,
  UserPlus,
  BarChart3,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";

const TABS = [
  { href: "/crm", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/crm/leads", label: "Leads", icon: UserPlus },
  { href: "/crm/companies", label: "Companies", icon: Building2 },
  { href: "/crm/contacts", label: "Contacts", icon: Contact },
  { href: "/crm/deals", label: "Deals", icon: Target },
  { href: "/crm/quotations", label: "Quotations", icon: FileText },
  { href: "/crm/contracts", label: "Contracts", icon: ScrollText },
  { href: "/crm/tasks", label: "Tasks", icon: ClipboardList },
  { href: "/crm/calendar", label: "Calendar", icon: CalendarDays },
  { href: "/crm/activities", label: "Activities", icon: Activity },
  { href: "/crm/import", label: "Import", icon: Upload },
  { href: "/crm/reports", label: "Reports", icon: BarChart3 },
];

export default function CrmNav() {
  const pathname = usePathname();
  return (
    <div className="-mx-1 flex gap-1 overflow-x-auto pb-1">
      {TABS.map(({ href, label, icon: Icon, exact }) => {
        const active = exact
          ? pathname === href
          : pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
              active ? "bg-secondary text-white" : "text-primary/70 hover:bg-white"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        );
      })}
    </div>
  );
}
