"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { adminFetch } from "@/lib/api";
import { settingsApi } from "@/lib/settings";
import { withStaffStepUp } from "@/lib/staff-step-up";

type Access = { ip_allowlist_enabled: boolean; ip_allowlist: string[] };

/** Optional admin IP allowlist. Off by default; your current IP must be on the list. */
export default function AdminAccessPanel() {
  const { getApiToken } = useAdminAuth();
  const [cfg, setCfg] = useState<Access | null>(null);
  const [text, setText] = useState("");
  const [myIp, setMyIp] = useState<string>("");
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const token = await getApiToken();
      const all = (await settingsApi.config(token)) as { config?: Record<string, unknown> };
      const a = (all.config?.admin_access as Access) ?? {
        ip_allowlist_enabled: false,
        ip_allowlist: [],
      };
      setCfg(a);
      setText(a.ip_allowlist.join("\n"));
      const me = await adminFetch<{ ip: string }>("/v1/admin/security/my-ip", token).catch(
        () => null
      );
      setMyIp(me?.ip ?? "");
    })();
  }, [getApiToken]);

  if (!cfg) return <p className="text-sm text-muted">Loading…</p>;
  const list = text
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter(Boolean);
  const risky =
    cfg.ip_allowlist_enabled && list.length > 0 && Boolean(myIp) && !list.includes(myIp);

  async function save() {
    setMsg(null);
    try {
      const token = await getApiToken();
      await withStaffStepUp(token, () =>
        settingsApi.updateConfig(
          token,
          "admin_access",
          { ...cfg, ip_allowlist: list },
          "Admin access"
        )
      );
      setMsg("Saved. Takes effect within 30 seconds.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <label className="flex items-center justify-between gap-4 rounded-xl border border-primary/10 p-4">
        <span>
          <span className="block font-semibold text-primary">Restrict Admin to these IPs</span>
          <span className="text-xs text-muted">
            Off by default. When on, Admin only works from the addresses below (an empty list means
            off).
          </span>
        </span>
        <input
          type="checkbox"
          aria-label="Restrict Admin to listed IPs"
          checked={cfg.ip_allowlist_enabled}
          onChange={(e) => setCfg({ ...cfg, ip_allowlist_enabled: e.target.checked })}
          className="h-5 w-5"
        />
      </label>
      <label className="block text-sm font-semibold text-primary">
        Allowed IPs or ranges (one per line, e.g. 203.0.113.7 or 203.0.113.0/24)
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          className="mt-1 w-full rounded-xl border border-primary/15 p-3 font-mono text-sm"
        />
      </label>
      <p className="text-xs text-muted">
        Your current IP: <strong>{myIp || "unknown"}</strong>{" "}
        {myIp && !list.includes(myIp) ? (
          <button
            type="button"
            className="font-semibold underline"
            onClick={() => setText([...list, myIp].join("\n"))}
          >
            Add it
          </button>
        ) : null}
      </p>
      {risky ? (
        <p role="alert" className="text-sm text-red-700">
          Your current IP is not listed exactly. Unless a range above covers it, saving will lock
          you out of Admin.
        </p>
      ) : null}
      <div className="flex items-center gap-3">
        <Button onClick={() => void save()}>Save</Button>
        {msg ? <span className="text-sm text-muted">{msg}</span> : null}
      </div>
    </div>
  );
}
