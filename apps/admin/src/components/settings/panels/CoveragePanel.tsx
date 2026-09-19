"use client";

import { useEffect, useMemo, useState } from "react";
import { Save } from "lucide-react";
import { Button, Textarea } from "@/components/crm/primitives";
import { SECTION_DESCRIPTIONS } from "@/lib/settings-metadata";
import { BindingBadge, SettingsCard, SettingsPageHeader } from "../ui/SettingsPrimitives";

type Coverage = { areas: unknown[]; zones: unknown[] };

type Props = {
  data: unknown;
  saving?: boolean;
  onSave: (value: Coverage, reason: string) => Promise<void>;
};

function normalize(raw: unknown): Coverage {
  if (typeof raw === "object" && raw !== null) {
    const o = raw as Record<string, unknown>;
    return {
      areas: Array.isArray(o.areas) ? o.areas : [],
      zones: Array.isArray(o.zones) ? o.zones : [],
    };
  }
  return { areas: [], zones: [] };
}

export default function CoveragePanel({ data, saving, onSave }: Props) {
  const initial = useMemo(() => normalize(data), [data]);
  const [areasJson, setAreasJson] = useState(() => JSON.stringify(initial.areas, null, 2));
  const [zonesJson, setZonesJson] = useState(() => JSON.stringify(initial.zones, null, 2));
  const [reason, setReason] = useState("");
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setAreasJson(JSON.stringify(initial.areas, null, 2));
    setZonesJson(JSON.stringify(initial.zones, null, 2));
    setDirty(false);
    setError(null);
  }, [initial]);

  async function handleSave() {
    try {
      const areas = JSON.parse(areasJson) as unknown;
      const zones = JSON.parse(zonesJson) as unknown;
      if (!Array.isArray(areas) || !Array.isArray(zones)) {
        setError("Areas and zones must be JSON arrays");
        return;
      }
      setError(null);
      await onSave({ areas, zones }, reason.trim() || "Updated coverage");
      setDirty(false);
      setReason("");
    } catch {
      setError("Invalid JSON");
    }
  }

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title="Coverage"
        description={SECTION_DESCRIPTIONS.coverage}
        actions={
          <div className="flex items-center gap-2">
            <BindingBadge effect="wired" />
            <Button variant="primary" disabled={!dirty || saving} onClick={() => void handleSave()}>
              <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        }
      />
      <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
        Active cities gate retail quotes by matching the city name inside the pickup formatted
        address. Leave areas empty for unrestricted service. Zone JSON is ops reference only until
        pricing zone math consumes it.
      </p>
      <SettingsCard
        title="Service areas"
        description="Cities / regions where PorterChain sells capacity"
      >
        <Textarea
          value={areasJson}
          onChange={(e) => {
            setAreasJson(e.target.value);
            setDirty(true);
          }}
          rows={8}
          className="font-mono text-xs"
        />
      </SettingsCard>
      <SettingsCard
        title="Delivery zones"
        description="Zone overrides (policy — not yet applied in quote math)"
      >
        <Textarea
          value={zonesJson}
          onChange={(e) => {
            setZonesJson(e.target.value);
            setDirty(true);
          }}
          rows={6}
          className="font-mono text-xs"
        />
      </SettingsCard>
      <label className="block text-sm">
        <span className="text-xs font-medium text-muted">Change reason</span>
        <input
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="mt-1 w-full rounded-xl border border-primary/10 px-3 py-2 text-sm"
          placeholder="Optional"
        />
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
