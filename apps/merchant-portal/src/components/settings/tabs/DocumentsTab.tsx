"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import { settingsApi, type BusinessDocument } from "@/lib/settings";

export function DocumentsTab({
  documents,
  onRefresh,
  getToken,
  orgId,
}: {
  documents: BusinessDocument[];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [name, setName] = useState("");
  const [docType, setDocType] = useState("hst");
  const [reference, setReference] = useState("");
  const [error, setError] = useState<string | null>(null);

  const add = async () => {
    if (!name.trim()) return;
    setError(null);
    try {
      const token = await getToken();
      await settingsApi.addDocument(
        token,
        { name: name.trim(), doc_type: docType, reference: reference.trim() || undefined },
        orgId
      );
      setName("");
      setReference("");
      await onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add document");
    }
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Company documents</h2>
      <p className="mt-1 text-sm text-muted">
        HST letters, insurance, and WSIB references this company file needs. Files stay as a named
        record — PorterChain does not store the PDF here.
      </p>
      <ul className="mt-4 space-y-2 text-sm">
        {documents.length === 0 && <li className="text-muted">No documents on file yet</li>}
        {documents.map((doc) => (
          <li key={doc.id} className="flex justify-between gap-3 border-b border-primary/5 py-2">
            <span>
              <span className="font-medium">{doc.name}</span>
              <span className="ml-2 text-muted">{doc.type}</span>
              {doc.reference ? <span className="ml-2 text-muted">{doc.reference}</span> : null}
            </span>
            <button
              type="button"
              className="text-xs text-red-600"
              onClick={() =>
                void getToken().then((t) =>
                  settingsApi.deleteDocument(t, doc.id, orgId).then(onRefresh)
                )
              }
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="rounded-lg border px-3 py-2 text-sm"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <select
          className="rounded-lg border px-3 py-2 text-sm"
          value={docType}
          onChange={(e) => setDocType(e.target.value)}
        >
          <option value="hst">HST / tax</option>
          <option value="insurance">Insurance</option>
          <option value="wsib">WSIB</option>
          <option value="other">Other</option>
        </select>
        <input
          className="rounded-lg border px-3 py-2 text-sm"
          placeholder="Reference (optional)"
          value={reference}
          onChange={(e) => setReference(e.target.value)}
        />
        <Button size="sm" onClick={() => void add()}>
          Add document
        </Button>
      </div>
      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
    </section>
  );
}
