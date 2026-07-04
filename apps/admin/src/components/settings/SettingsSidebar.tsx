"use client";

import type { LucideIcon } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import {
  SECTION_ICONS,
  SETTINGS_GROUP_LABELS,
  type SettingsGroupId,
} from "@/lib/settings-metadata";
import type { SettingsSection } from "@/lib/settings";

type Props = {
  sections: SettingsSection[];
  activeId: string;
  onSelect: (id: string) => void;
};

export default function SettingsSidebar({ sections, activeId, onSelect }: Props) {
  const groups = sections.reduce<Record<string, SettingsSection[]>>((acc, s) => {
    acc[s.group] = acc[s.group] ?? [];
    acc[s.group].push(s);
    return acc;
  }, {});

  const order: SettingsGroupId[] = [
    "overview",
    "company",
    "access",
    "communications",
    "integrations",
    "operations",
    "modules",
    "platform",
  ];

  return (
    <nav className="space-y-6">
      {order.map((groupId) => {
        const items = groups[groupId];
        if (!items?.length) return null;
        return (
          <div key={groupId}>
            <p className="mb-2 px-2 text-[10px] font-bold uppercase tracking-widest text-muted">
              {SETTINGS_GROUP_LABELS[groupId]}
            </p>
            <ul className="space-y-0.5">
              {items.map((s) => {
                const Icon = (SECTION_ICONS[s.id] ?? SECTION_ICONS.dashboard) as LucideIcon;
                const active = activeId === s.id;
                return (
                  <li key={s.id}>
                    <button
                      type="button"
                      onClick={() => onSelect(s.id)}
                      className={cn(
                        "flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-sm transition-colors",
                        active
                          ? "bg-secondary text-white shadow-sm shadow-secondary/25"
                          : "text-primary/70 hover:bg-gray-bg hover:text-primary"
                      )}
                    >
                      <Icon className={cn("h-4 w-4 shrink-0", active ? "text-white/90" : "text-muted")} />
                      <span className="truncate font-medium">{s.label}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}
