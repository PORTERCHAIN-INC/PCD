"use client";

import { useState } from "react";
import { Button } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { merchants } from "@/lib/merchants";

/**
 * FSA rate card: rebuild from the merchant's pickup (drive time + km per FSA) and
 * export. Edit any cell in the table below; edited cells stay through rebuilds.
 */
export default function FsaRateCardActions({
  merchantId,
  onRebuilt,
}: {
  merchantId: string;
  onRebuilt: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const rebuild = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const card = await merchants.regenerateFsaRateCard(await getApiToken(), merchantId);
      setMsg(`Rate card rebuilt: ${card.cells.length} FSAs priced from the pickup.`);
      onRebuilt();
    } catch (e) {
      const code = e instanceof Error ? e.message : "";
      setMsg(
        code.includes("pickup_required")
          ? "Add a pickup address with a location first."
          : code.includes("routing_unavailable")
            ? "Routing is offline. Try again in a minute."
            : "Rebuild failed."
      );
    } finally {
      setBusy(false);
    }
  };

  const open = async (format: "pdf" | "csv") => {
    const res = await fetch(`/api/porterchain${merchants.fsaRateCardPath(merchantId, format)}`, {
      credentials: "include",
      headers: { Authorization: `Bearer ${await getApiToken()}` },
    });
    if (!res.ok) return setMsg("Export failed.");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(await res.blob());
    a.download = `fsa-rate-card-${merchantId.slice(0, 8)}.${format}`;
    a.click();
  };

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-primary/10 bg-white p-4">
      <p className="mr-auto text-sm text-primary">
        <strong>FSA rate card</strong>
        <span className="text-muted">
          {" "}
          · priced by drive time and km from the pickup. Edited cells are kept on rebuild.
        </span>
      </p>
      <Button onClick={() => void rebuild()} disabled={busy}>
        {busy ? "Rebuilding…" : "Rebuild from pickup"}
      </Button>
      <Button variant="secondary" onClick={() => void open("pdf")}>
        PDF
      </Button>
      <Button variant="secondary" onClick={() => void open("csv")}>
        CSV
      </Button>
      {msg ? <p className="w-full text-sm text-muted">{msg}</p> : null}
    </div>
  );
}
