"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { KeyRound, MonitorSmartphone, Shield, Trash2 } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { adminFetch } from "@/lib/api";
import { clearStaffSession } from "@/lib/staff-session";
import { publicEnv } from "@/lib/env";
import { createPasskey, credentialToJson, passkeysSupported } from "@/lib/staff-webauthn";
import { fetchStaffSecurityStatus, type StaffSecurityEvent } from "@/lib/staff-security";

type StaffSessionRow = {
  session_id: string;
  email: string;
  role: string;
  created_at: number;
  expires_at: number;
  absolute_expires_at: number;
  is_current: boolean;
  client_ip?: string | null;
  user_agent?: string | null;
  device_label?: string | null;
};

type PasskeyRow = {
  id: string;
  credential_id: string;
  device_label: string | null;
  created_at: string | null;
  last_used_at: string | null;
};

function fmtTs(epoch: number | string | null | undefined): string {
  if (epoch == null || epoch === "") return "—";
  const ms = typeof epoch === "number" ? epoch * 1000 : Date.parse(epoch);
  if (!Number.isFinite(ms)) return "—";
  return new Date(ms).toLocaleString();
}

export default function AccountSecurityPage() {
  const router = useRouter();
  const { getApiToken, authReady } = useAdminAuth();
  const [sessions, setSessions] = useState<StaffSessionRow[]>([]);
  const [passkeys, setPasskeys] = useState<PasskeyRow[]>([]);
  const [events, setEvents] = useState<StaffSecurityEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const token = await getApiToken();
    const [s, p, status] = await Promise.all([
      adminFetch<{ sessions: StaffSessionRow[] }>("/v1/auth/staff/sessions", token),
      adminFetch<{ passkeys: PasskeyRow[] }>("/v1/auth/staff/passkeys", token),
      fetchStaffSecurityStatus(token),
    ]);
    setSessions(s.sessions || []);
    setPasskeys(p.passkeys || []);
    setEvents(status.events || []);
  }, [getApiToken]);

  useEffect(() => {
    if (!authReady) return;
    void reload().catch((e) => setError(e instanceof Error ? e.message : "load_failed"));
  }, [authReady, reload]);

  async function revokeSession(sessionId: string, isCurrent: boolean) {
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      const token = await getApiToken();
      const res = await adminFetch<{ ok: boolean; signed_out?: boolean }>(
        `/v1/auth/staff/sessions/${encodeURIComponent(sessionId)}`,
        token,
        { method: "DELETE" }
      );
      if (res.signed_out || isCurrent) {
        await clearStaffSession(publicEnv.porterchainApiUrl);
        router.replace("/sign-in?reason=session_revoked");
        return;
      }
      setMsg("Session revoked.");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "revoke_failed");
    } finally {
      setBusy(false);
    }
  }

  async function revokeOthers() {
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      const token = await getApiToken();
      const res = await adminFetch<{ revoked: number }>(
        "/v1/auth/staff/sessions/revoke-others",
        token,
        { method: "POST" }
      );
      setMsg(`Revoked ${res.revoked} other session(s).`);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "revoke_others_failed");
    } finally {
      setBusy(false);
    }
  }

  async function registerPasskey() {
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      const token = await getApiToken();
      const options = await adminFetch<Record<string, unknown> & { challenge_id?: string }>(
        "/v1/auth/staff/passkey/register/options",
        token,
        { method: "POST" }
      );
      const cred = await createPasskey(options);
      await adminFetch("/v1/auth/staff/passkey/register/verify", token, {
        method: "POST",
        body: JSON.stringify({
          challenge_id: String(options.challenge_id || ""),
          credential: credentialToJson(cred),
          device_label: "This device",
        }),
      });
      setMsg("Passkey saved.");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "passkey_failed");
    } finally {
      setBusy(false);
    }
  }

  async function removePasskey(id: string) {
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      const token = await getApiToken();
      await adminFetch(`/v1/auth/staff/passkeys/${encodeURIComponent(id)}`, token, {
        method: "DELETE",
      });
      setMsg("Passkey removed.");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "passkey_delete_failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-secondary">Account</p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-primary">
            <Shield className="h-6 w-6 text-secondary" />
            Security
          </h1>
          <p className="mt-1 text-sm text-muted">
            Sessions and passkeys for your staff IdP account. Role changes and deactivation wipe all
            sessions.
          </p>
        </div>
        <Link href="/dashboard" className="text-sm font-medium text-secondary underline">
          Back
        </Link>
      </div>

      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      )}
      {msg && (
        <p className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-900">
          {msg}
        </p>
      )}

      <section className="rounded-2xl border border-primary/10 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-primary">
            <MonitorSmartphone className="h-4 w-4 text-secondary" />
            Active sessions
          </h2>
          <button
            type="button"
            disabled={busy || sessions.filter((s) => !s.is_current).length === 0}
            onClick={() => void revokeOthers()}
            className="rounded-lg border border-primary/15 px-3 py-1.5 text-xs font-semibold text-primary hover:bg-gray-bg disabled:opacity-50"
          >
            Sign out other devices
          </button>
        </div>
        {sessions.length === 0 ? (
          <p className="text-sm text-muted">No sessions indexed yet.</p>
        ) : (
          <ul className="space-y-2">
            {sessions.map((s) => (
              <li
                key={s.session_id}
                className="flex items-center justify-between gap-3 rounded-xl border border-primary/8 px-3 py-2.5"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-primary">
                    {s.is_current ? "This device" : s.device_label || "Other device"}
                    {s.is_current && s.device_label ? (
                      <span className="ml-2 font-normal text-muted">· {s.device_label}</span>
                    ) : null}
                    <span className="ml-2 font-mono text-xs text-muted">
                      …{s.session_id.slice(-8)}
                    </span>
                  </p>
                  <p className="text-xs text-muted">
                    {s.client_ip ? `${s.client_ip} · ` : ""}
                    Started {fmtTs(s.created_at)} · idle until {fmtTs(s.expires_at)} · hard cap{" "}
                    {fmtTs(s.absolute_expires_at)}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void revokeSession(s.session_id, s.is_current)}
                  className="shrink-0 rounded-lg border border-red-200 px-2.5 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                >
                  Revoke
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-2xl border border-primary/10 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-primary">
            <KeyRound className="h-4 w-4 text-secondary" />
            Passkeys
          </h2>
          {passkeysSupported() && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void registerPasskey()}
              className="rounded-lg bg-secondary px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#1d4ed8] disabled:opacity-50"
            >
              Add passkey
            </button>
          )}
        </div>
        {passkeys.length === 0 ? (
          <p className="text-sm text-muted">
            No passkeys yet — add one for phishing-resistant sign-in.
          </p>
        ) : (
          <ul className="space-y-2">
            {passkeys.map((p) => (
              <li
                key={p.id}
                className="flex items-center justify-between gap-3 rounded-xl border border-primary/8 px-3 py-2.5"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-primary">
                    {p.device_label || "Passkey"}
                  </p>
                  <p className="text-xs text-muted">
                    Added {fmtTs(p.created_at)} · last used {fmtTs(p.last_used_at)}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void removePasskey(p.id)}
                  className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-red-200 px-2.5 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-2xl border border-primary/10 bg-white p-5 shadow-sm">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-primary">
          <Shield className="h-4 w-4 text-secondary" />
          Recent security events
        </h2>
        {events.length === 0 ? (
          <p className="text-sm text-muted">No recent login or recovery events yet.</p>
        ) : (
          <ul className="space-y-2">
            {events.map((ev, idx) => (
              <li
                key={`${ev.kind}-${ev.ts}-${idx}`}
                className="rounded-xl border border-primary/8 px-3 py-2.5 text-sm"
              >
                <p className="font-medium text-primary">{ev.kind.replace(/_/g, " ")}</p>
                <p className="text-xs text-muted">
                  {fmtTs(ev.ts)}
                  {ev.detail?.device_label ? ` · ${String(ev.detail.device_label)}` : ""}
                  {ev.detail?.client_ip ? ` · ${String(ev.detail.client_ip)}` : ""}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
