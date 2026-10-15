"use client";

import { useRef } from "react";
import { ACCEPT, type PendingFile } from "@/lib/attachments";

const MAX = 10 * 1024 * 1024;

export function BookingFilesPicker({
  files,
  onChange,
}: {
  files: PendingFile[];
  onChange: (f: PendingFile[]) => void;
}) {
  const ref = useRef<HTMLInputElement>(null);
  function add(list: FileList | null) {
    const next = [...files];
    for (const file of Array.from(list ?? [])) {
      if (file.size > MAX || next.length >= 10) continue;
      next.push({ file, required: true, saveForLocation: false });
    }
    onChange(next);
  }
  return (
    <div
      className="rounded-xl border border-dashed border-primary/20 p-3 text-sm"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        add(e.dataTransfer.files);
      }}
    >
      <p className="font-medium text-primary">Pickup documents (optional)</p>
      <p className="text-muted">
        E.g. a warehouse pickup authorization. Only the assigned driver can open it. PDF, JPG, PNG
        or HEIC, up to 10 MB.
      </p>
      {files.length > 0 && (
        <ul className="mt-2 space-y-1">
          {files.map((f, i) => (
            <li key={i} className="flex flex-wrap items-center gap-3">
              <span className="font-medium">{f.file.name}</span>
              <label className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={f.required}
                  onChange={(e) =>
                    onChange(
                      files.map((x, j) => (j === i ? { ...x, required: e.target.checked } : x))
                    )
                  }
                />
                Must be shown at pickup
              </label>
              <label className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={f.saveForLocation}
                  onChange={(e) =>
                    onChange(
                      files.map((x, j) =>
                        j === i ? { ...x, saveForLocation: e.target.checked } : x
                      )
                    )
                  }
                />
                Use for every booking from this address
              </label>
              <button
                type="button"
                className="text-red-600 hover:underline"
                onClick={() => onChange(files.filter((_, j) => j !== i))}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
      <button
        type="button"
        className="mt-2 font-semibold text-secondary hover:underline"
        onClick={() => ref.current?.click()}
      >
        + Attach document
      </button>
      <input
        ref={ref}
        type="file"
        accept={ACCEPT}
        multiple
        hidden
        onChange={(e) => add(e.target.files)}
      />
    </div>
  );
}
