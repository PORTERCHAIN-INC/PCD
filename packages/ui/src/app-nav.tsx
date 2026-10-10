"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentType,
  type ReactNode,
} from "react";
import { ChevronsLeft, ChevronsRight, Menu, Search, X, type LucideIcon } from "lucide-react";
import { cn } from "./utils";

/**
 * One navigation system for every web persona (admin, merchant, customer, driver):
 * collapsible desktop rail, 390px drawer + optional bottom tabs, ⌘K palette, badges.
 * Active state = navy fill + one accent bar. Next.js-free: apps pass their own Link.
 */
export type AppNavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  description?: string;
  /** Count of things needing action; hidden when 0/undefined. */
  badge?: number;
  /** Extra palette search terms. */
  keywords?: string;
};
export type AppNavGroup = { id: string; label: string; items: AppNavItem[] };
export type PaletteEntry = {
  href: string;
  label: string;
  group: string;
  keywords?: string;
  hint?: string;
};
type LinkLike = ComponentType<{
  href: string;
  className?: string;
  children: ReactNode;
  onClick?: () => void;
  "aria-current"?: "page" | undefined;
  "aria-label"?: string;
  title?: string;
}>;

const fmtBadge = (n: number) => (n > 99 ? "99+" : String(n));

function Badge({ n, dot }: { n?: number; dot?: boolean }) {
  if (!n) return null;
  if (dot)
    return (
      <span
        className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-secondary ring-2 ring-white"
        aria-hidden
      />
    );
  return (
    <span className="ml-auto min-w-5 rounded-full bg-secondary px-1.5 text-center text-[11px] font-bold leading-5 text-white tabular-nums">
      {fmtBadge(n)}
    </span>
  );
}

function NavList({
  groups,
  isActive,
  Link,
  collapsed,
  onNavigate,
}: {
  groups: AppNavGroup[];
  isActive: (href: string) => boolean;
  Link: LinkLike;
  collapsed?: boolean;
  onNavigate?: () => void;
}) {
  return (
    <nav aria-label="Main" className="space-y-4">
      {groups.map((g) => (
        <div key={g.id}>
          {!collapsed && g.label ? (
            <p className="mb-1 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-muted">
              {g.label}
            </p>
          ) : null}
          <ul className="space-y-0.5">
            {g.items.map((it) => {
              const active = isActive(it.href);
              const Icon = it.icon;
              return (
                <li key={it.href}>
                  <Link
                    href={it.href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    title={collapsed ? it.label : it.description}
                    aria-label={it.badge ? `${it.label}, ${it.badge} need action` : undefined}
                    className={cn(
                      "relative flex min-h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors",
                      collapsed && "justify-center px-0",
                      active
                        ? "bg-primary text-white"
                        : "text-primary/75 hover:bg-primary/5 hover:text-primary"
                    )}
                  >
                    {active ? (
                      <span
                        className="absolute left-0 top-2 bottom-2 w-1 rounded-r bg-secondary"
                        aria-hidden
                      />
                    ) : null}
                    <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden />
                    {collapsed ? (
                      <Badge n={it.badge} dot />
                    ) : (
                      <>
                        <span className="truncate">{it.label}</span>
                        <Badge n={it.badge} />
                      </>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

export function CommandPalette({
  entries,
  open,
  onClose,
  onSelect,
  search,
  placeholder = "Jump to any page or setting…",
}: {
  entries: PaletteEntry[];
  open: boolean;
  onClose: () => void;
  onSelect: (href: string) => void;
  /** Optional live search (orders, merchants…) merged under the static entries. */
  search?: (q: string) => Promise<PaletteEntry[]>;
  placeholder?: string;
}) {
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);
  const [remote, setRemote] = useState<PaletteEntry[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQ("");
      setIdx(0);
      setRemote([]);
      window.setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  useEffect(() => {
    if (!open || !search || q.trim().length < 2) {
      setRemote([]);
      return;
    }
    let live = true;
    const t = window.setTimeout(() => {
      search(q.trim())
        .then((r) => live && setRemote(r))
        .catch(() => live && setRemote([]));
    }, 200);
    return () => {
      live = false;
      window.clearTimeout(t);
    };
  }, [q, open, search]);

  const results = useMemo(() => {
    const term = q.trim().toLowerCase();
    const local = !term
      ? entries.slice(0, 12)
      : entries
          .map((e) => {
            const hay = `${e.label} ${e.group} ${e.keywords ?? ""}`.toLowerCase();
            const label = e.label.toLowerCase();
            const score = label.startsWith(term)
              ? 0
              : label.includes(term)
                ? 1
                : hay.includes(term)
                  ? 2
                  : 9;
            return { e, score };
          })
          .filter((x) => x.score < 9)
          .sort((a, b) => a.score - b.score)
          .slice(0, 12)
          .map((x) => x.e);
    return [...local, ...remote].slice(0, 16);
  }, [q, entries, remote]);

  if (!open) return null;
  const pick = (e?: PaletteEntry) => {
    if (!e) return;
    onClose();
    onSelect(e.href);
  };
  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center bg-primary/40 p-3 pt-[12vh] backdrop-blur-sm"
      onMouseDown={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Quick search"
        className="w-full max-w-xl overflow-hidden rounded-2xl bg-white shadow-2xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-primary/10 px-4">
          <Search className="h-4 w-4 text-muted" aria-hidden />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setIdx(0);
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setIdx((i) => Math.min(i + 1, results.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setIdx((i) => Math.max(i - 1, 0));
              } else if (e.key === "Enter") {
                e.preventDefault();
                pick(results[idx]);
              } else if (e.key === "Escape") onClose();
            }}
            placeholder={placeholder}
            aria-label="Search pages and settings"
            role="combobox"
            aria-expanded="true"
            aria-controls="cmdk-list"
            className="h-12 min-w-0 flex-1 bg-transparent text-sm text-primary outline-none"
          />
          <kbd className="rounded border border-primary/15 px-1.5 text-[10px] text-muted">Esc</kbd>
        </div>
        <ul id="cmdk-list" role="listbox" className="max-h-[60vh] overflow-y-auto p-2">
          {results.length === 0 ? (
            <li className="px-3 py-6 text-center text-sm text-muted">No match</li>
          ) : (
            results.map((e, i) => (
              <li key={`${e.group}-${e.href}-${e.label}`} role="option" aria-selected={i === idx}>
                <button
                  type="button"
                  onMouseEnter={() => setIdx(i)}
                  onClick={() => pick(e)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm",
                    i === idx ? "bg-primary text-white" : "text-primary"
                  )}
                >
                  <span className="min-w-0 flex-1 truncate font-medium">{e.label}</span>
                  <span
                    className={cn("shrink-0 text-xs", i === idx ? "text-white/70" : "text-muted")}
                  >
                    {e.hint ?? e.group}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}

/** Flatten nav groups into palette entries (pages are always searchable). */
export function navToPalette(groups: AppNavGroup[]): PaletteEntry[] {
  return groups.flatMap((g) =>
    g.items.map((it) => ({
      href: it.href,
      label: it.label,
      group: g.label || "Go to",
      keywords: `${it.description ?? ""} ${it.keywords ?? ""}`,
    }))
  );
}

export function AppShell({
  brand,
  brandHref,
  groups,
  isActive,
  Link,
  navigate,
  actions,
  title,
  palette = [],
  search,
  bottomTabs,
  storageKey = "pc.nav.collapsed",
  mainClassName,
  banner,
  children,
}: {
  brand: { mark: string; name: string; sub?: string; logo?: ReactNode };
  brandHref: string;
  groups: AppNavGroup[];
  isActive: (href: string) => boolean;
  Link: LinkLike;
  navigate: (href: string) => void;
  /** Right side of the top bar (bell, account…). */
  actions?: ReactNode;
  title?: ReactNode;
  /** Extra palette entries (settings sections, sub-pages, actions). */
  palette?: PaletteEntry[];
  search?: (q: string) => Promise<PaletteEntry[]>;
  /** 390px bottom tabs (max 4); the rest stays in the drawer. */
  bottomTabs?: AppNavItem[];
  storageKey?: string;
  mainClassName?: string;
  banner?: ReactNode;
  children: ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [cmdk, setCmdk] = useState(false);

  useEffect(() => {
    setCollapsed(window.localStorage.getItem(storageKey) === "1");
  }, [storageKey]);
  const toggle = useCallback(() => {
    setCollapsed((c) => {
      window.localStorage.setItem(storageKey, c ? "0" : "1");
      return !c;
    });
  }, [storageKey]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmdk((v) => !v);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "\\") {
        e.preventDefault();
        toggle();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);

  const entries = useMemo(() => {
    const seen = new Set<string>();
    return [...navToPalette(groups), ...palette].filter((e) => {
      const k = `${e.href}|${e.label}`;
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });
  }, [groups, palette]);

  const brandEl = (small?: boolean) => (
    <Link
      href={brandHref}
      className="flex min-w-0 items-center gap-2.5"
      aria-label={`${brand.name} home`}
    >
      {brand.logo ?? (
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-sm font-extrabold text-white">
          {brand.mark}
        </span>
      )}
      {!small ? (
        <span className="min-w-0">
          <span className="block truncate text-sm font-bold leading-tight text-primary">
            {brand.name}
          </span>
          {brand.sub ? (
            <span className="block truncate text-[11px] leading-tight text-muted">{brand.sub}</span>
          ) : null}
        </span>
      ) : null}
    </Link>
  );

  const searchBtn = (wide: boolean) => (
    <button
      type="button"
      onClick={() => setCmdk(true)}
      aria-label="Search (Ctrl or Command K)"
      className={cn(
        "flex min-h-10 items-center gap-2 rounded-xl border border-primary/10 bg-white text-sm text-muted hover:border-primary/25",
        wide ? "w-full px-3" : "w-10 justify-center"
      )}
    >
      <Search className="h-4 w-4 shrink-0" aria-hidden />
      {wide ? (
        <>
          <span className="flex-1 text-left">Search</span>
          <kbd className="rounded border border-primary/15 px-1.5 text-[10px]">⌘K</kbd>
        </>
      ) : null}
    </button>
  );

  return (
    <div className="flex h-dvh min-w-0 bg-gray-bg">
      <aside
        className={cn(
          "hidden shrink-0 flex-col border-r border-primary/10 bg-white transition-[width] lg:flex",
          collapsed ? "w-[72px]" : "w-60"
        )}
      >
        <div className={cn("flex h-14 items-center px-4", collapsed && "justify-center px-0")}>
          {brandEl(collapsed)}
        </div>
        <div className={cn("px-3 pb-3", collapsed && "flex justify-center")}>
          {searchBtn(!collapsed)}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
          <NavList groups={groups} isActive={isActive} Link={Link} collapsed={collapsed} />
        </div>
        <button
          type="button"
          onClick={toggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title="Ctrl/⌘ + \\"
          className="flex h-11 items-center justify-center gap-2 border-t border-primary/10 text-xs font-medium text-muted hover:text-primary"
        >
          {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
          {!collapsed ? "Collapse" : null}
        </button>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="relative z-40 flex h-14 shrink-0 items-center gap-2 border-b border-primary/10 bg-white px-2 sm:px-4">
          <button
            type="button"
            onClick={() => setDrawer(true)}
            aria-label="Open menu"
            className="flex h-10 w-10 items-center justify-center rounded-xl text-primary hover:bg-primary/5 lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="lg:hidden">{brandEl(true)}</div>
          <div className="min-w-0 flex-1 truncate text-sm font-semibold text-primary">{title}</div>
          <div className="lg:hidden">{searchBtn(false)}</div>
          <div className="flex shrink-0 items-center gap-1 sm:gap-2">{actions}</div>
        </header>
        {banner}
        <main
          className={cn(
            "min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-clip",
            bottomTabs?.length ? "pb-20 lg:pb-0" : null,
            mainClassName
          )}
        >
          {children}
        </main>
        {bottomTabs?.length ? (
          <nav
            aria-label="Tabs"
            className="fixed inset-x-0 bottom-0 z-40 border-t border-primary/10 bg-white pb-[env(safe-area-inset-bottom)] lg:hidden"
          >
            <ul
              className="grid"
              style={{ gridTemplateColumns: `repeat(${bottomTabs.length + 1}, minmax(0,1fr))` }}
            >
              {bottomTabs.map((t) => {
                const active = isActive(t.href);
                const Icon = t.icon;
                return (
                  <li key={t.href}>
                    <Link
                      href={t.href}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "relative flex min-h-14 flex-col items-center justify-center gap-0.5 text-[11px] font-semibold",
                        active ? "text-primary" : "text-muted"
                      )}
                    >
                      {active ? (
                        <span
                          className="absolute top-0 h-0.5 w-8 rounded bg-secondary"
                          aria-hidden
                        />
                      ) : null}
                      <Icon className="h-5 w-5" aria-hidden />
                      {t.label}
                      {t.badge ? (
                        <span className="absolute right-[22%] top-1.5 min-w-4 rounded-full bg-secondary px-1 text-[10px] leading-4 text-white">
                          {fmtBadge(t.badge)}
                        </span>
                      ) : null}
                    </Link>
                  </li>
                );
              })}
              <li>
                <button
                  type="button"
                  onClick={() => setDrawer(true)}
                  className="flex min-h-14 w-full flex-col items-center justify-center gap-0.5 text-[11px] font-semibold text-muted"
                >
                  <Menu className="h-5 w-5" aria-hidden />
                  More
                </button>
              </li>
            </ul>
          </nav>
        ) : null}
      </div>

      {drawer ? (
        <div
          className="fixed inset-0 z-[90] lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Menu"
        >
          <button
            type="button"
            aria-label="Close menu"
            className="absolute inset-0 bg-primary/40"
            onClick={() => setDrawer(false)}
          />
          <div className="absolute inset-y-0 left-0 flex w-[86vw] max-w-xs flex-col bg-white shadow-2xl">
            <div className="flex h-14 items-center justify-between px-4">
              {brandEl()}
              <button
                type="button"
                onClick={() => setDrawer(false)}
                aria-label="Close menu"
                className="flex h-10 w-10 items-center justify-center rounded-xl hover:bg-primary/5"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="px-3 pb-3">{searchBtn(true)}</div>
            <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-6">
              <NavList
                groups={groups}
                isActive={isActive}
                Link={Link}
                onNavigate={() => setDrawer(false)}
              />
            </div>
          </div>
        </div>
      ) : null}

      <CommandPalette
        entries={entries}
        open={cmdk}
        onClose={() => setCmdk(false)}
        onSelect={navigate}
        search={search}
      />
    </div>
  );
}
