"use client";

import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { createApiKey, listApiKeys, revokeApiKey, type ApiKeyRecord } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useEffect, useState } from "react";

export default function ApiPage() {
  const { getApiToken, orgId, isSignedIn, isLoaded } = useMerchantAuth();
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [newSecret, setNewSecret] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [environment, setEnvironment] = useState<"sandbox" | "production">("sandbox");

  async function load() {
    const token = await getApiToken();
    setKeys(await listApiKeys(token, orgId));
  }

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch keys on mount
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn, orgId]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    const token = await getApiToken();
    const key = await createApiKey(token, { name: name || "API Key", environment }, orgId);
    setNewSecret(key.secret || null);
    setName("");
    await load();
  }

  async function onRevoke(id: string) {
    const token = await getApiToken();
    await revokeApiKey(token, id, orgId);
    await load();
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-primary">API Integration</h1>
        <p className="text-sm text-muted">Generate keys, manage webhooks, sandbox and production modes</p>
      </div>

      {newSecret && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm">
          <p className="font-semibold text-amber-900">Copy your API key now — it won&apos;t be shown again</p>
          <code className="mt-2 block break-all rounded bg-white p-2 font-mono text-xs">{newSecret}</code>
          <button type="button" className="mt-2 text-xs text-muted underline" onClick={() => setNewSecret(null)}>
            Dismiss
          </button>
        </div>
      )}

      <form onSubmit={onCreate} className="flex flex-wrap items-end gap-3 rounded-2xl border border-primary/10 bg-white p-6">
        <div>
          <label className="text-sm font-medium">Key name</label>
          <input
            className="mt-1 block rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Production integration"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Environment</label>
          <select
            className="mt-1 block rounded-xl border border-primary/15 px-3 py-2 text-sm"
            value={environment}
            onChange={(e) => setEnvironment(e.target.value as "sandbox" | "production")}
          >
            <option value="sandbox">Sandbox</option>
            <option value="production">Production</option>
          </select>
        </div>
        <Button type="submit">Generate API key</Button>
      </form>

      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Active keys</h2>
        <p className="mt-1 text-xs text-muted">Rate limit: 60 requests/minute per key (default)</p>
        <ul className="mt-4 divide-y divide-primary/5">
          {keys.map((k) => (
            <li key={k.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
              <div>
                <p className="font-medium">{k.name}</p>
                <p className="font-mono text-xs text-muted">
                  {k.key_prefix}… · {k.environment} · {formatDate(k.created_at)}
                </p>
              </div>
              <button type="button" className="text-xs text-red-600" onClick={() => onRevoke(k.id)}>
                Revoke
              </button>
            </li>
          ))}
          {keys.length === 0 && <li className="py-4 text-muted">No API keys yet</li>}
        </ul>
      </section>

      <section className="rounded-2xl border border-primary/10 bg-white p-6 text-sm text-muted">
        <h2 className="font-semibold text-primary">API documentation</h2>
        <p className="mt-2">
          Merchant API base: <code className="rounded bg-gray-bg px-1">{process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL || "http://localhost:8001"}/v1/merchant</code>
        </p>
        <p className="mt-2">Authenticate with <code className="rounded bg-gray-bg px-1">Authorization: Bearer &lt;api_key&gt;</code></p>
      </section>
    </div>
  );
}
