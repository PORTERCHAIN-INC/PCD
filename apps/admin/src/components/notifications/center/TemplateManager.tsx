"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { cn } from "@porterchain/ui/utils";
import { centerApi, type TemplatePreview } from "@/lib/notificationCenter";
import { PrimaryButton, QuietButton, Tone, when } from "./ui";

const PLACEHOLDERS = "{merchant} {tracking} {eta_minutes} {window_label} {order_number}";

export default function TemplateManager() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const ready = isLoaded && isSignedIn;
  const qc = useQueryClient();
  const [key, setKey] = useState("cx_delivered");
  const [lang, setLang] = useState<"en" | "fr">("en");
  const [subject, setSubject] = useState("");
  const [intro, setIntro] = useState("");
  const [draft, setDraft] = useState<TemplatePreview | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const { data: list } = useQuery({
    queryKey: ["nc-templates"],
    enabled: ready,
    queryFn: async () => centerApi.templates(await getApiToken()),
  });
  const { data: saved } = useQuery({
    queryKey: ["nc-preview", key, lang],
    enabled: ready,
    queryFn: async () => centerApi.preview(await getApiToken(), key, lang),
  });
  const { data: history } = useQuery({
    queryKey: ["nc-history", key],
    enabled: ready,
    queryFn: async () => centerApi.history(await getApiToken(), key),
  });

  useEffect(() => {
    const latest = history?.find((h) => h.lang === lang);
    setSubject(latest?.active ? (latest.subject ?? "") : "");
    setIntro(latest?.active ? (latest.intro ?? "") : "");
    setDraft(null);
    setMsg(null);
  }, [key, lang, history]);

  const preview = draft ?? saved;
  const tryDraft = async () => {
    setMsg(null);
    try {
      setDraft(await centerApi.previewDraft(await getApiToken(), key, { lang, subject, intro }));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Preview failed");
    }
  };
  const save = async () => {
    try {
      const r = await centerApi.saveCopy(await getApiToken(), key, { lang, subject, intro });
      setMsg(
        r.active
          ? `Saved as v${r.version}. Live within 30 s.`
          : `v${r.version}: back to built-in copy.`
      );
      await qc.invalidateQueries({ queryKey: ["nc-history", key] });
      await qc.invalidateQueries({ queryKey: ["nc-preview", key] });
      await qc.invalidateQueries({ queryKey: ["nc-templates"] });
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    }
  };
  const test = async () => {
    const r = await centerApi.test(await getApiToken(), key, lang);
    setMsg(`Test queued to ${r.to} (your address only).`);
  };
  const shown = (list ?? []).filter((t) => !filter || t.key.includes(filter.toLowerCase()));

  return (
    <div className="grid gap-5 lg:grid-cols-[16rem_1fr]">
      <div>
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter templates"
          aria-label="Filter templates"
          className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm placeholder:text-slate-500 focus:border-[#2563eb] focus:outline-none focus:ring-2 focus:ring-[#2563eb]/30"
        />
        <ul className="mt-2 max-h-[18rem] overflow-y-auto rounded-2xl border border-slate-200 bg-white lg:max-h-[40rem]">
          {shown.map((t) => (
            <li key={t.key}>
              <button
                type="button"
                onClick={() => setKey(t.key)}
                className={cn(
                  "flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm",
                  key === t.key ? "bg-slate-900 text-white" : "text-slate-800 hover:bg-slate-50"
                )}
              >
                <span className="truncate font-mono text-xs">{t.key}</span>
                <span className="flex shrink-0 gap-1 text-[10px] font-bold">
                  {t.receiver ? (
                    <span className={key === t.key ? "text-[#93c5fd]" : "text-[#1d4ed8]"}>RCV</span>
                  ) : null}
                  {t.french ? <span>FR</span> : null}
                  {t.edited_en || t.edited_fr ? (
                    <span className={key === t.key ? "text-amber-300" : "text-amber-700"}>
                      EDIT
                    </span>
                  ) : null}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="min-w-0 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-mono text-sm font-bold text-slate-900">{key}</h2>
          <div
            role="group"
            aria-label="Language"
            className="inline-flex rounded-full bg-slate-100 p-1"
          >
            {(["en", "fr"] as const).map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => setLang(l)}
                aria-pressed={lang === l}
                className={cn(
                  "rounded-full px-4 py-1 text-sm font-semibold",
                  lang === l ? "bg-white text-slate-900 shadow" : "text-slate-700"
                )}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <label
            className="block text-[11px] font-semibold uppercase tracking-wide text-slate-600"
            htmlFor="tm-subject"
          >
            Subject
          </label>
          <input
            id="tm-subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder={saved?.subject ?? "Built-in subject"}
            className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm placeholder:text-slate-500 focus:border-[#2563eb] focus:outline-none focus:ring-2 focus:ring-[#2563eb]/30"
          />
          <label
            className="mt-3 block text-[11px] font-semibold uppercase tracking-wide text-slate-600"
            htmlFor="tm-intro"
          >
            Intro
          </label>
          <textarea
            id="tm-intro"
            value={intro}
            onChange={(e) => setIntro(e.target.value)}
            rows={3}
            placeholder="Built-in intro"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm placeholder:text-slate-500 focus:border-[#2563eb] focus:outline-none focus:ring-2 focus:ring-[#2563eb]/30"
          />
          <p className="mt-1 text-xs text-slate-600">
            Placeholders: <span className="font-mono">{PLACEHOLDERS}</span>. Layout, links and the
            legal footer stay fixed. Leave both empty to go back to built-in copy.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <PrimaryButton onClick={save}>Save version</PrimaryButton>
            <QuietButton onClick={tryDraft}>Preview draft</QuietButton>
            <QuietButton onClick={test}>Send test to me</QuietButton>
            {msg ? (
              <span className="text-sm text-slate-700" role="status">
                {msg}
              </span>
            ) : null}
          </div>
        </div>

        {preview ? (
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <div className="border-b border-slate-200 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                {draft ? "Draft preview" : "Live preview"} · {preview.audience} ·{" "}
                {preview.lang.toUpperCase()}
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-900">{preview.subject}</p>
            </div>
            <iframe
              title={`Preview ${key} ${lang}`}
              sandbox=""
              srcDoc={preview.html}
              className="h-[34rem] w-full"
            />
            <details className="border-t border-slate-200 px-4 py-3">
              <summary className="cursor-pointer text-sm font-semibold text-slate-800">
                Plain-text part
              </summary>
              <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-700">{preview.text}</pre>
            </details>
          </div>
        ) : null}

        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            Version history
          </h3>
          {history?.length ? (
            <ul className="mt-2 divide-y divide-slate-100 rounded-2xl border border-slate-200 bg-white">
              {history.map((h) => (
                <li
                  key={h.id}
                  className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 text-sm"
                >
                  <span className="min-w-0">
                    <span className="font-semibold tabular-nums text-slate-900">
                      v{h.version} · {h.lang.toUpperCase()}
                    </span>{" "}
                    <span className="text-slate-700">
                      {h.subject || h.intro || "Reset to built-in"}
                    </span>
                  </span>
                  <span className="flex items-center gap-2 text-xs text-slate-600">
                    {h.created_by} · {when(h.created_at)}
                    {h.active && h.lang === lang ? <Tone tone="idle">saved</Tone> : null}
                    <QuietButton
                      onClick={() => {
                        setLang(h.lang === "fr" ? "fr" : "en");
                        setSubject(h.subject ?? "");
                        setIntro(h.intro ?? "");
                      }}
                    >
                      Restore
                    </QuietButton>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-slate-600">No edits. Built-in copy is live.</p>
          )}
        </div>
      </div>
    </div>
  );
}
