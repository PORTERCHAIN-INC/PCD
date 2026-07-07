"use client";

import { ExternalLink, Grid3X3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { publicEnv } from "@/lib/env";
import HeaderDropdown from "@/components/nav/HeaderDropdown";

type AppLink = {
  id: string;
  label: string;
  description: string;
  href: string;
  port?: number;
};

function getDriverAppLinks(): AppLink[] {
  return [
    {
      id: "website",
      label: "Website",
      description: "Public site & retail booking",
      href: process.env.NEXT_PUBLIC_WEBSITE_URL ?? "http://localhost:3000",
      port: 3000,
    },
    {
      id: "merchant",
      label: "Merchant Portal",
      description: "B2B bookings & billing",
      href: process.env.NEXT_PUBLIC_MERCHANT_PORTAL_URL ?? "http://localhost:3001",
      port: 3001,
    },
    {
      id: "customer",
      label: "Customer Portal",
      description: "Retail orders & support",
      href: process.env.NEXT_PUBLIC_CUSTOMER_PORTAL_URL ?? "http://localhost:3004",
      port: 3004,
    },
    {
      id: "admin",
      label: "Admin",
      description: "Operations console",
      href:
        process.env.NEXT_PUBLIC_ADMIN_PORTAL_URL ??
        process.env.NEXT_PUBLIC_ADMIN_URL ??
        "http://localhost:3002",
      port: 3002,
    },
    {
      id: "api",
      label: "Porterchain API",
      description: "API health & docs",
      href: `${publicEnv.porterchainApiUrl.replace(/\/$/, "")}/health`,
      port: 8001,
    },
  ];
}

export default function DriverAppsMenu() {
  const links = getDriverAppLinks();

  return (
    <HeaderDropdown
      align="right"
      width="xl"
      trigger={({ open, triggerProps }) => (
        <button
          type="button"
          {...triggerProps}
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-full border border-primary/10 bg-white text-primary shadow-sm transition hover:bg-gray-bg",
            open && "bg-gray-bg ring-2 ring-secondary/20"
          )}
          aria-label="Open apps and systems"
          title="Apps & systems"
        >
          <Grid3X3 className="h-4 w-4" />
        </button>
      )}
    >
      <div className="border-b border-primary/8 px-4 py-3">
        <p className="text-sm font-semibold text-primary">Porterchain ecosystem</p>
        <p className="text-xs text-muted">Jump to other apps & services</p>
      </div>
      <div className="grid max-h-[60dvh] grid-cols-2 gap-1 overflow-y-auto p-2">
        {links.map((link) => (
          <a
            key={link.id}
            href={link.href}
            target="_blank"
            rel="noopener noreferrer"
            className="flex flex-col items-start gap-1 rounded-xl border border-transparent px-3 py-3 text-left transition hover:border-primary/10 hover:bg-gray-bg"
          >
            <span className="flex items-center gap-1.5 text-sm font-semibold text-primary">
              <ExternalLink className="h-3.5 w-3.5 text-secondary" />
              {link.label}
            </span>
            <span className="text-[11px] leading-snug text-muted">{link.description}</span>
            {link.port && (
              <span className="mt-0.5 rounded-md bg-primary/5 px-1.5 py-0.5 font-mono text-[10px] text-muted">
                :{link.port}
              </span>
            )}
          </a>
        ))}
      </div>
    </HeaderDropdown>
  );
}
