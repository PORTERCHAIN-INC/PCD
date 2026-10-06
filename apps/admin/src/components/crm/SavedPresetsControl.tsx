"use client";

import { useEffect, useState } from "react";
import { Bookmark, ChevronDown, Trash2 } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { Button } from "@/components/crm/primitives";

type Props<T> = {
  storageKey: string;
  value: T;
  onLoad: (value: T) => void;
  /** Visible label for the control. */
  label?: string;
  className?: string;
};

function readPresets<T>(key: string): Record<string, T> {
  try {
    return JSON.parse(localStorage.getItem(key) || "{}") as Record<string, T>;
  } catch {
    return {};
  }
}

/**
 * Inline save / load for named localStorage presets — no browser prompt()/alert().
 */
export function SavedPresetsControl<T>({
  storageKey,
  value,
  onLoad,
  label = "Presets",
  className,
}: Props<T>) {
  const [open, setOpen] = useState(false);
  const [names, setNames] = useState<string[]>([]);
  const [draftName, setDraftName] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  function refresh() {
    setNames(Object.keys(readPresets<T>(storageKey)).sort());
  }

  useEffect(() => {
    if (open) refresh();
  }, [open, storageKey]);

  function save() {
    const name = draftName.trim();
    if (!name) {
      setMessage("Name this preset first");
      return;
    }
    const next = readPresets<T>(storageKey);
    next[name] = value;
    localStorage.setItem(storageKey, JSON.stringify(next));
    setDraftName("");
    setMessage(`Saved “${name}”`);
    refresh();
  }

  function load(name: string) {
    const presets = readPresets<T>(storageKey);
    if (!presets[name]) return;
    onLoad(presets[name]);
    setMessage(`Loaded “${name}”`);
    setOpen(false);
  }

  function remove(name: string) {
    const next = readPresets<T>(storageKey);
    delete next[name];
    localStorage.setItem(storageKey, JSON.stringify(next));
    refresh();
    setMessage(`Removed “${name}”`);
  }

  return (
    <div className={cn("relative", className)}>
      <Button
        type="button"
        variant="outline"
        className="text-xs"
        aria-expanded={open}
        onClick={() => {
          setMessage(null);
          setOpen((v) => !v);
        }}
      >
        <Bookmark className="h-3.5 w-3.5" />
        {label}
        <ChevronDown className={cn("h-3.5 w-3.5 opacity-70", open && "rotate-180")} />
      </Button>
      {open ? (
        <>
          <button
            type="button"
            className="fixed inset-0 z-20 cursor-default"
            aria-label="Close presets"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 z-30 mt-1 w-[min(18rem,calc(100vw-2rem))] rounded-xl border border-primary/10 bg-white p-3 shadow-lg">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted">
              Save current
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={draftName}
                onChange={(e) => setDraftName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") save();
                }}
                placeholder="Preset name"
                className="min-w-0 flex-1 rounded-lg border border-primary/10 px-2.5 py-1.5 text-sm"
              />
              <Button type="button" className="text-xs" onClick={save}>
                Save
              </Button>
            </div>

            <p className="mb-1.5 mt-3 text-[10px] font-semibold uppercase tracking-wide text-muted">
              Saved
            </p>
            {names.length === 0 ? (
              <p className="py-2 text-xs text-muted">No presets yet</p>
            ) : (
              <ul className="max-h-40 space-y-0.5 overflow-y-auto">
                {names.map((name) => (
                  <li key={name} className="flex items-center gap-1">
                    <button
                      type="button"
                      className="min-w-0 flex-1 truncate rounded-lg px-2 py-1.5 text-left text-sm hover:bg-gray-bg"
                      onClick={() => load(name)}
                    >
                      {name}
                    </button>
                    <button
                      type="button"
                      className="rounded-lg p-1.5 text-muted hover:bg-red-50 hover:text-red-600"
                      aria-label={`Delete ${name}`}
                      onClick={() => remove(name)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {message ? <p className="mt-2 text-xs text-secondary">{message}</p> : null}
          </div>
        </>
      ) : null}
    </div>
  );
}
