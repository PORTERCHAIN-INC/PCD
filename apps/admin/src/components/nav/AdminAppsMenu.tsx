"use client";

import { useState } from "react";
import { ExternalLink, Grid3X3, Loader2 } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { api } from "@/lib/api";
import { getSystemLinks, type SystemLink } from "@/lib/system-links";
import HeaderDropdown from "@/components/nav/HeaderDropdown";

export default function AdminAppsMenu() {
  const { getApiToken } = useAdminAuth();
  const [ssoLoading, setSsoLoading] = useState(false);
  const links = getSystemLinks().filter((l) => l.id !== "admin");

  async function openLink(link: SystemLink) {
    if (link.fleetbaseSso) {
      setSsoLoading(true);
      try {
        const token = await getApiToken();
        const session = await api.fleetbaseSso(token);
        window.open(session.console_url, "_blank", "noopener,noreferrer");
      } catch {
        window.open(link.href, "_blank", "noopener,noreferrer");
      } finally {
        setSsoLoading(false);
      }
    } else {
      window.open(link.href, "_blank", "noopener,noreferrer");
    }
  }

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
        <p className="text-sm font-semibold text-primary">Porterchain ecosystem</p>
        <p className="text-xs text-muted">Jump to other apps & services</p>
      </div>
      <div className="grid max-h-[60dvh] grid-cols-2 gap-1 overflow-y-auto p-2">
        {links.map((link) => (
          <button
            key={link.id}
            type="button"
            disabled={ssoLoading && link.fleetbaseSso}
            onClick={() => void openLink(link)}
            className="flex flex-col items-start gap-1 rounded-xl border border-transparent px-3 py-3 text-left transition hover:border-primary/10 hover:bg-gray-bg disabled:opacity-60"
          >
            <span className="flex items-center gap-1.5 text-sm font-semibold text-primary">
              {ssoLoading && link.fleetbaseSso ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-secondary" />
              ) : (
                <ExternalLink className="h-3.5 w-3.5 text-secondary" />
              )}
              {link.label}
            </span>
            <span className="text-[11px] leading-snug text-muted">{link.description}</span>
            {link.port && (
              <span className="mt-0.5 rounded-md bg-primary/5 px-1.5 py-0.5 font-mono text-[10px] text-muted">
                :{link.port}
              </span>
            )}
          </button>
        ))}
      </div>
    </HeaderDropdown>
  );
}
