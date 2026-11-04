"use client";

import { useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import { setMyDisplayName } from "@/lib/api";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { Field } from "./Field";

/** L34: the signed-in person edits their own display name (shown in the account menu). */
export function YourNameCard({
  getToken,
  orgId,
}: {
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const { session } = useMerchantAuth();
  const [name, setName] = useState(session?.display_name ?? "");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => setName(session?.display_name ?? ""), [session?.display_name]);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      await setMyDisplayName(await getToken(), name, orgId);
      setMsg("Saved.");
      window.location.reload();
    } catch (err) {
      setMsg(`${"Couldn't save:"} ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form
      onSubmit={(e) => void save(e)}
      className="rounded-2xl border border-primary/10 bg-white p-6 space-y-3"
    >
      <h2 className="text-lg font-semibold text-primary">{"Your name"}</h2>
      <p className="text-sm text-primary/70">
        {"Shown in the account menu for your own sign-in only."}
      </p>
      <Field label={"Display name"} value={name} onChange={setName} />
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={busy}>
          {"Save name"}
        </Button>
        {msg ? (
          <span role="status" className="text-sm text-primary/70">
            {msg}
          </span>
        ) : null}
      </div>
    </form>
  );
}
