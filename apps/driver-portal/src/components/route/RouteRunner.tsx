"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, Check, ChevronDown, MapPin, MoreHorizontal, Navigation, Package } from "lucide-react";
import { driverApi } from "@/lib/api";
import {
  KIND_LABEL,
  checklistItemCount,
  currentPosition,
  etaClock,
  isPickup,
  mapsUrl,
  photoToDataUrl,
  primaryAction,
  type CheckinEvent,
  type DriverDispatchRoute,
  type RouteStop,
} from "@/lib/dispatch-route";
import { cn } from "@/lib/utils";

const FAIL_REASONS = ["Nobody home", "Address wrong", "Refused", "Damaged", "Closed", "Unsafe"];

export default function RouteRunner() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["dispatch-route"], queryFn: driverApi.dispatchRoute, refetchInterval: 30_000 });
  const route = q.data?.route ?? null;

  if (q.isLoading) return <RouteSkeleton />;
  if (q.isError) {
    return (
      <Shell>
        <Empty title="Can't load your route" body="Check your signal, then try again." action="Retry" onAction={() => q.refetch()} />
      </Shell>
    );
  }
  if (!route || route.total === 0) {
    return (
      <Shell>
        <Empty title="No route yet" body="When dispatch commits today's plan, your stops appear here in order." action="Refresh" onAction={() => q.refetch()} />
      </Shell>
    );
  }
  return <Runner route={route} onRoute={(r) => qc.setQueryData(["dispatch-route"], { route: r })} />;
}

function Runner({ route, onRoute }: { route: DriverDispatchRoute; onRoute: (r: DriverDispatchRoute | null) => void }) {
  const stop = route.next_index != null ? route.stops[route.next_index] : null;
  const pct = Math.round((100 * route.done) / Math.max(route.total, 1));
  return (
    <Shell>
      <header className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Today&apos;s route</p>
          <p className="mt-1 text-5xl font-black tabular-nums tracking-tight text-[#0a1628]">
            {route.done}
            <span className="text-slate-500">/{route.total}</span>
          </p>
          <p className="text-sm text-slate-600">stops done</p>
        </div>
        <p className="pb-1 text-right text-sm font-medium capitalize text-slate-600">{route.vehicle_class.replace("_", " ")}</p>
      </header>
      <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full bg-[#38bdf8] transition-all" style={{ width: `${pct}%` }} />
      </div>

      {stop ? (
        <StopCard key={stop.keys.join(",") + stop.status} stop={stop} n={(route.next_index ?? 0) + 1} onRoute={onRoute} />
      ) : (
        <div className="mt-10 rounded-3xl bg-[#0a1628] p-8 text-center text-white">
          <Check className="mx-auto h-12 w-12 text-[#38bdf8]" aria-hidden />
          <p className="mt-4 text-3xl font-black">Route complete</p>
          <p className="mt-2 text-slate-300">{route.total} stops. Nice work.</p>
        </div>
      )}

      <Upcoming route={route} />
    </Shell>
  );
}

function StopCard({ stop, n, onRoute }: { stop: RouteStop; n: number; onRoute: (r: DriverDispatchRoute | null) => void }) {
  const action = primaryAction(stop);
  const pickup = isPickup(stop.kind);
  const atStop = stop.status === "arrived";
  const [ticked, setTicked] = useState<Set<string>>(new Set());
  const [photo, setPhoto] = useState<string | null>(null);
  const [menu, setMenu] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const checklist = useQuery({
    queryKey: ["dispatch-checklist", stop.order_id],
    queryFn: () => driverApi.dispatchChecklist(stop.order_id),
    enabled: pickup && atStop,
  });
  const items = checklist.data?.items ?? [];
  const itemCount = checklistItemCount(checklist.data ?? null);

  const send = useMutation({
    mutationFn: async (v: { event: CheckinEvent; note?: string }) => {
      const pos = await currentPosition();
      return driverApi.dispatchCheckin({
        keys: stop.keys,
        event: v.event,
        ...(pos ?? {}),
        ...(v.note ? { note: v.note } : {}),
        ...(v.event === "delivered" && photo ? { pod_photo: photo } : {}),
      });
    },
    onSuccess: (r) => onRoute(r.route),
    onError: (e: Error) => setErr(e.message.startsWith("pod_required") ? "Take a delivery photo first." : e.message.replaceAll("_", " ")),
  });

  useEffect(() => setErr(null), [ticked, photo]);

  const checklistDone = !pickup || !atStop || (items.length > 0 ? ticked.size >= items.length : !checklist.isLoading);
  const podDone = !(atStop && stop.needs_pod) || Boolean(photo);
  const ready = Boolean(action) && checklistDone && podDone && !send.isPending;
  const label = !action
    ? ""
    : action.event === "picked_up" && itemCount
      ? `Picked up · ${itemCount} item${itemCount === 1 ? "" : "s"}`
      : action.label;
  const maps = mapsUrl(stop);

  return (
    <section className="mt-8 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm" aria-label={`Stop ${n}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-sky-800">
            Stop {n} · {KIND_LABEL[stop.kind]}
          </p>
          <p className="mt-2 break-words text-2xl font-black leading-tight text-[#0a1628]">{stop.address ?? "Address on file"}</p>
          <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600">
            <span className="font-semibold text-slate-800">{stop.order_number ?? "—"}</span>
            <span className="inline-flex items-center gap-1"><Package className="h-4 w-4" aria-hidden />{stop.boxes} box{stop.boxes === 1 ? "" : "es"}</span>
            {stop.eta_s > 0 && stop.status === "pending" ? <span>ETA {etaClock(stop.eta_s)}</span> : null}
          </p>
        </div>
        <div className="relative shrink-0">
          <button
            type="button"
            aria-label="More actions"
            aria-expanded={menu}
            onClick={() => setMenu((m) => !m)}
            className="flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 text-slate-700 hover:bg-slate-50"
          >
            <MoreHorizontal className="h-6 w-6" aria-hidden />
          </button>
          {menu ? (
            <div className="absolute right-0 z-10 mt-2 w-60 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl" role="menu">
              <p className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Can&apos;t complete</p>
              {FAIL_REASONS.map((r) => (
                <button
                  key={r}
                  role="menuitem"
                  type="button"
                  className="block min-h-12 w-full rounded-xl px-3 text-left text-base text-slate-800 hover:bg-slate-100"
                  onClick={() => {
                    setMenu(false);
                    if (window.confirm(`Mark stop ${n} as failed: ${r}?`)) send.mutate({ event: "failed", note: r });
                  }}
                >
                  {r}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      {stop.notes ? <p className="mt-4 rounded-2xl bg-amber-50 p-3 text-sm text-amber-900">{stop.notes}</p> : null}

      {pickup && atStop ? (
        <div className="mt-5">
          <p className="text-sm font-semibold text-slate-800">Load checklist</p>
          {checklist.isLoading ? (
            <div className="mt-2 space-y-2" aria-busy="true">
              {[0, 1].map((i) => <div key={i} className="h-14 animate-pulse rounded-2xl bg-slate-100" />)}
            </div>
          ) : (
            <ul className="mt-2 space-y-2">
              {items.map((it) => {
                const id = it.item_key ?? it.boxes[0]?.package_id ?? it.label;
                const on = ticked.has(id);
                return (
                  <li key={id}>
                    <button
                      type="button"
                      aria-pressed={on}
                      onClick={() => setTicked((s) => { const x = new Set(s); if (x.has(id)) x.delete(id); else x.add(id); return x; })}
                      className={cn(
                        "flex min-h-14 w-full items-center gap-3 rounded-2xl border px-4 text-left transition",
                        on ? "border-[#0a1628] bg-[#0a1628] text-white" : "border-slate-200 bg-white text-slate-900",
                      )}
                    >
                      <span className={cn("flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2", on ? "border-[#38bdf8] bg-[#38bdf8]" : "border-slate-300")}>
                        {on ? <Check className="h-4 w-4 text-[#0a1628]" aria-hidden /> : null}
                      </span>
                      <span className="flex-1 text-base font-semibold">{it.label}</span>
                      <span className={cn("text-sm", on ? "text-slate-300" : "text-slate-600")}>{it.rule ?? "1 box"}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
          {items.some((i) => i.rule) ? (
            <p className="mt-2 text-xs text-slate-600">Multi-box items count as one item. Load every box.</p>
          ) : null}
        </div>
      ) : null}

      {atStop && stop.needs_pod ? (
        <div className="mt-5">
          <input ref={fileRef} type="file" accept="image/*" capture="environment" className="sr-only" aria-label="Delivery photo"
            onChange={async (e) => {
              const f = e.target.files?.[0];
              if (f) setPhoto(await photoToDataUrl(f).catch(() => null));
            }}
          />
          {photo ? (
            <button type="button" onClick={() => fileRef.current?.click()} className="flex w-full items-center gap-3 rounded-2xl border border-slate-200 p-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={photo} alt="Delivery photo" className="h-16 w-16 rounded-xl object-cover" />
              <span className="text-sm font-semibold text-slate-800">Photo ready · tap to retake</span>
            </button>
          ) : (
            <button type="button" onClick={() => fileRef.current?.click()}
              className="flex min-h-16 w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-slate-300 text-base font-semibold text-slate-800 hover:border-[#0a1628]">
              <Camera className="h-6 w-6" aria-hidden /> Take delivery photo
            </button>
          )}
        </div>
      ) : null}

      {err ? <p role="alert" className="mt-4 text-sm font-medium text-red-700">{err}</p> : null}

      <div className="mt-6 flex gap-3">
        {maps && stop.status === "pending" ? (
          <a href={maps} target="_blank" rel="noreferrer" aria-label="Navigate"
            className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-slate-300 text-[#0a1628]">
            <Navigation className="h-6 w-6" aria-hidden />
          </a>
        ) : null}
        {action ? (
          <button
            type="button"
            disabled={!ready}
            onClick={() => send.mutate({ event: action.event })}
            className="h-16 flex-1 rounded-2xl bg-[#0a1628] text-lg font-black text-white transition enabled:hover:bg-[#13254a] disabled:bg-slate-300 disabled:text-slate-600"
          >
            {send.isPending ? "Saving…" : label}
          </button>
        ) : null}
      </div>
    </section>
  );
}

function Upcoming({ route }: { route: DriverDispatchRoute }) {
  const [open, setOpen] = useState(false);
  const rest = route.stops.map((s, i) => ({ s, i })).filter(({ i }) => i !== route.next_index);
  if (!rest.length) return null;
  return (
    <section className="mt-8">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open}
        className="flex min-h-12 w-full items-center justify-between rounded-2xl px-1 text-sm font-semibold text-slate-700">
        All stops ({route.total})
        <ChevronDown className={cn("h-5 w-5 transition", open && "rotate-180")} aria-hidden />
      </button>
      {open ? (
        <ol className="mt-2 divide-y divide-slate-100 rounded-2xl border border-slate-200 bg-white">
          {rest.map(({ s, i }) => (
            <li key={s.keys.join(",")} className="flex items-center gap-3 px-4 py-3">
              <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold",
                s.status === "done" ? "bg-[#0a1628] text-white" : s.status === "failed" ? "bg-red-100 text-red-800" : "bg-slate-100 text-slate-700")}>
                {s.status === "done" ? <Check className="h-4 w-4" aria-hidden /> : i + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-500">{KIND_LABEL[s.kind]}</span>
                <span className="block truncate text-sm text-slate-900">{s.address ?? s.fsa ?? "—"}</span>
              </span>
              <MapPin className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto w-full max-w-xl px-5 pb-24 pt-6">{children}</main>;
}

function Empty({ title, body, action, onAction }: { title: string; body: string; action: string; onAction: () => void }) {
  return (
    <div className="mt-16 text-center">
      <p className="text-3xl font-black text-[#0a1628]">{title}</p>
      <p className="mx-auto mt-3 max-w-xs text-slate-600">{body}</p>
      <button type="button" onClick={onAction} className="mt-8 h-14 rounded-2xl bg-[#0a1628] px-8 text-base font-bold text-white">
        {action}
      </button>
    </div>
  );
}

function RouteSkeleton() {
  return (
    <Shell>
      <div aria-busy="true" aria-label="Loading route">
        <div className="h-3 w-28 animate-pulse rounded bg-slate-200" />
        <div className="mt-3 h-12 w-32 animate-pulse rounded-xl bg-slate-200" />
        <div className="mt-6 h-2 w-full animate-pulse rounded-full bg-slate-200" />
        <div className="mt-8 h-64 animate-pulse rounded-3xl bg-slate-100" />
      </div>
    </Shell>
  );
}
