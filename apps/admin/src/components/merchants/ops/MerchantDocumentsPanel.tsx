"use client";

import { useRef, useState } from "react";
import { FileText, Upload } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchantOps, type MerchantDoc } from "@/lib/merchant-ops";
import {
  ActionMenu,
  Dialog,
  Empty,
  FieldLabel,
  Panel,
  Pill,
  PrimaryAction,
  QuietButton,
  ReasonDialog,
  SkeletonRows,
  inputClass,
} from "./ui";

const MAX_BYTES = 10 * 1024 * 1024;
const TYPES = ["application/pdf", "image/png", "image/jpeg"];

/** COI, signed contracts, tax forms. PDF/PNG/JPG up to 10 MB. Every download is logged. */
export function MerchantDocumentsPanel({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data, error } = useApiData((t) => merchantOps.documents(t, id), [id, version], {
    key: `merchant-docs-${id}`,
  });
  const fileRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [kind, setKind] = useState("insurance_coi");
  const [expires, setExpires] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);
  const [del, setDel] = useState<MerchantDoc | null>(null);

  const fileErr = !file
    ? null
    : !TYPES.includes(file.type)
      ? "PDF, PNG or JPG only."
      : file.size > MAX_BYTES
        ? "Over 10 MB."
        : null;

  function reset() {
    setOpen(false);
    setFile(null);
    setExpires("");
    if (fileRef.current) fileRef.current.value = "";
  }

  async function upload() {
    if (!file || fileErr) return;
    setBusy(true);
    setMsg(null);
    try {
      const t = await getApiToken();
      await merchantOps.uploadDocument(t, id, file, kind, expires || undefined);
      setMsg({ text: `${file.name} uploaded` });
      reset();
      setVersion((v) => v + 1);
    } catch (e) {
      setMsg({ text: e instanceof Error ? e.message : "Upload failed", bad: true });
    } finally {
      setBusy(false);
    }
  }

  async function act(fn: (t: string) => Promise<unknown>, done?: string) {
    setMsg(null);
    setBusy(true);
    try {
      await fn(await getApiToken());
      if (done) setMsg({ text: done });
      setVersion((v) => v + 1);
    } catch (e) {
      setMsg({ text: e instanceof Error ? e.message : "Failed", bad: true });
    } finally {
      setBusy(false);
      setDel(null);
    }
  }

  const items = data?.items ?? [];
  const expired = items.filter((d) => d.expired).length;
  const hasCoi = items.some((d) => d.kind === "insurance_coi" && !d.expired);

  return (
    <Panel
      title="Documents"
      aside={
        <PrimaryAction onClick={() => setOpen(true)}>
          <Upload className="h-4 w-4" aria-hidden /> Upload
        </PrimaryAction>
      }
    >
      {!data && !error ? (
        <SkeletonRows rows={3} label="Loading documents" />
      ) : error ? (
        <Empty title="Couldn't load documents" hint={error} />
      ) : items.length === 0 ? (
        <Empty
          icon={<FileText className="h-6 w-6" aria-hidden />}
          title="No documents yet"
          hint="Start with the certificate of insurance. PDF, PNG or JPG, up to 10 MB."
        />
      ) : (
        <>
          <p className="text-sm text-slate-600 tabular-nums">
            {items.length} files
            {expired ? (
              <span className="font-semibold text-red-700"> · {expired} expired</span>
            ) : null}
            {!hasCoi ? (
              <span className="font-semibold text-amber-800">
                {" "}
                · no valid insurance certificate
              </span>
            ) : null}
          </p>
          <ul className="mt-4 divide-y divide-primary/5 border-t border-primary/5">
            {items.map((d) => (
              <li key={d.id} className="flex items-center gap-3 py-3">
                <FileText className="h-5 w-5 shrink-0 text-primary/60" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold text-primary">{d.kind_label}</p>
                  <p className="truncate text-xs text-slate-600">
                    {d.filename} · {Math.max(1, Math.round(d.size_bytes / 1024))} KB
                    {d.expires_on ? ` · expires ${d.expires_on}` : ""}
                  </p>
                </div>
                {d.expired ? <Pill tone="red">Expired</Pill> : null}
                <ActionMenu
                  label={`Actions for ${d.filename}`}
                  items={[
                    {
                      label: "Download",
                      onSelect: () => void act((t) => merchantOps.downloadDocument(t, id, d)),
                    },
                    { label: "Delete", tone: "danger", onSelect: () => setDel(d) },
                  ]}
                />
              </li>
            ))}
          </ul>
        </>
      )}
      {msg ? (
        <p
          role="status"
          className={cn(
            "mt-3 text-sm font-semibold",
            msg.bad ? "text-red-700" : "text-emerald-700"
          )}
        >
          {msg.text}
        </p>
      ) : null}
      <p className="mt-4 text-xs text-slate-600">
        Downloads are logged. Files are wiped if the merchant is erased.
      </p>

      <Dialog
        open={open}
        onClose={reset}
        title="Upload a document"
        description="PDF, PNG or JPG, up to 10 MB."
        footer={
          <>
            <QuietButton onClick={reset}>Cancel</QuietButton>
            <PrimaryAction disabled={busy || !file || !!fileErr} onClick={() => void upload()}>
              {busy ? "Uploading…" : "Upload"}
            </PrimaryAction>
          </>
        }
      >
        <FieldLabel label="Type">
          <select className={inputClass} value={kind} onChange={(e) => setKind(e.target.value)}>
            {Object.entries(data?.kinds ?? { insurance_coi: "Certificate of insurance" }).map(
              ([k, l]) => (
                <option key={k} value={k}>
                  {l}
                </option>
              )
            )}
          </select>
        </FieldLabel>
        <FieldLabel
          label="File"
          hint={fileErr ?? (file ? `${file.name} · ${Math.ceil(file.size / 1024)} KB` : undefined)}
        >
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf,image/png,image/jpeg"
            aria-invalid={!!fileErr}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-primary file:mr-3 file:min-h-11 file:rounded-full file:border-0 file:bg-slate-100 file:px-4 file:font-semibold file:text-primary"
          />
        </FieldLabel>
        <FieldLabel label="Expires" hint="Optional. We flag it once it passes.">
          <input
            type="date"
            className={inputClass}
            value={expires}
            onChange={(e) => setExpires(e.target.value)}
          />
        </FieldLabel>
      </Dialog>
      <ReasonDialog
        open={del != null}
        title={`Delete ${del?.kind_label ?? "document"}?`}
        description="The file is wiped now. The change history keeps its name and your reason."
        confirm="Delete"
        tone="danger"
        busy={busy}
        onCancel={() => setDel(null)}
        onConfirm={(reason) =>
          del &&
          void act(
            (t) => merchantOps.deleteDocument(t, id, del.id, reason),
            `${del.filename} deleted`
          )
        }
      />
    </Panel>
  );
}
