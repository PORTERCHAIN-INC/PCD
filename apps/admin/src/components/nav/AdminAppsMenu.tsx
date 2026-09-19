"use client";

import { ExternalLink, Grid3X3 } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { getSystemLinks } from "@/lib/system-links";
import HeaderDropdown from "@/components/nav/HeaderDropdown";

export default function AdminAppsMenu() {
  const links = getSystemLinks().filter((l) => l.id !== "admin");

  const portals = links.filter((l) => ["website", "merchant", "customer", "driver"].includes(l.id));
  const tools = links.filter((l) => !["website", "merchant", "customer", "driver"].includes(l.id));

  return (
    <HeaderDropdown
      align="right"
      width="xl"
      trigger={({ open, triggerProps }) => (
        <button
          type="button"
          {...triggerProps}
          className={cn(
            "group relative flex h-10 w-10 items-center justify-center rounded-full border border-primary/10 bg-white text-primary shadow-sm transition hover:bg-gray-bg",
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
        <p className="text-sm font-semibold text-primary">PorterChain network</p>
        <p className="text-xs text-muted">Portals, API, and bonded tools</p>
      </div>

      <div className="max-h-[55dvh] overflow-y-auto p-2">
        <p className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted">
          Portals
        </p>
        <div className="grid grid-cols-2 gap-1">
          {portals.map((link) => (
            <AppTile
              key={link.id}
              label={link.label}
              description={link.description}
              host={link.host}
              port={link.port}
              onClick={() => window.open(link.href, "_blank", "noopener,noreferrer")}
            />
          ))}
        </div>

        <p className="mt-3 px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted">
          Tools
        </p>
        <div className="grid grid-cols-2 gap-1">
          {tools.map((link) => (
            <AppTile
              key={link.id}
              label={link.label}
              description={link.description}
              host={link.host}
              port={link.port}
              onClick={() => window.open(link.href, "_blank", "noopener,noreferrer")}
            />
          ))}
        </div>
      </div>
    </HeaderDropdown>
  );
}

function AppTile({
  label,
  description,
  host,
  port,
  onClick,
}: {
  label: string;
  description: string;
  host?: string;
  port?: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex flex-col items-start gap-1 rounded-xl border border-transparent px-3 py-2.5 text-left transition hover:border-primary/10 hover:bg-gray-bg"
    >
      <span className="flex items-center gap-1.5 text-sm font-semibold text-primary">
        <ExternalLink className="h-3.5 w-3.5 text-secondary" />
        {label}
      </span>
      <span className="text-[11px] leading-snug text-muted">{description}</span>
      {(host || port) && (
        <span className="mt-0.5 rounded-md bg-primary/5 px-1.5 py-0.5 font-mono text-[10px] text-muted">
          {host ?? `:${port}`}
        </span>
      )}
    </button>
  );
}
