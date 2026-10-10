"use client";

/**
 * Merchant ops design kit. Same language as the lead inbox: navy (`primary`) for
 * type and structure, one bright accent (`secondary`) reserved for the single
 * primary action on a screen. Numbers first, secondary actions in menus,
 * designed empty and loading states, AA contrast, 44px touch targets at 390px.
 */

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { MoreHorizontal, X } from "lucide-react";
import { cn } from "@porterchain/ui/utils";

export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p
      className={cn(
        "text-[11px] font-semibold tracking-[0.18em] text-secondary uppercase",
        className
      )}
    >
      {children}
    </p>
  );
}

export function PageHead({
  eyebrow,
  title,
  sub,
  action,
}: {
  eyebrow: string;
  title: ReactNode;
  sub?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <Eyebrow>{eyebrow}</Eyebrow>
        <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-primary sm:text-4xl">
          {title}
        </h1>
        {sub ? <p className="mt-1 text-sm text-slate-600">{sub}</p> : null}
      </div>
      {action}
    </header>
  );
}

/** The one accent button on a screen. */
export function PrimaryAction({
  children,
  className,
  tone = "accent",
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "accent" | "danger" }) {
  return (
    <button
      {...rest}
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-5 text-sm font-bold text-white shadow-sm",
        tone === "danger" ? "bg-red-700" : "bg-secondary",
        "hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
    >
      {children}
    </button>
  );
}

export const primaryLinkClass =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-secondary px-5 text-sm font-bold text-white shadow-sm hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary";

/** Quiet navy-outline button for the non-primary choices that must stay visible. */
export function QuietButton({
  children,
  className,
  tone = "default",
  square,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  tone?: "default" | "danger";
  square?: boolean;
}) {
  return (
    <button
      {...rest}
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-full border text-sm font-semibold",
        square ? "w-11" : "px-4",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary",
        "disabled:cursor-not-allowed disabled:opacity-50",
        tone === "danger"
          ? "border-red-200 text-red-700 hover:bg-red-50"
          : "border-primary/15 text-primary hover:bg-slate-50",
        className
      )}
    >
      {children}
    </button>
  );
}

/** Big number, small label. Tone only when the number is bad news. */
export function Stat({
  label,
  value,
  hint,
  tone = "default",
  onClick,
  active,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "bad" | "good";
  onClick?: () => void;
  active?: boolean;
}) {
  const body = (
    <>
      <span className="block text-[11px] font-semibold tracking-[0.14em] text-slate-600 uppercase">
        {label}
      </span>
      <span
        className={cn(
          "mt-1 block text-2xl font-extrabold tracking-tight tabular-nums sm:text-3xl",
          tone === "bad" ? "text-red-700" : tone === "good" ? "text-emerald-700" : "text-primary"
        )}
      >
        {value}
      </span>
      {hint ? <span className="mt-0.5 block text-xs text-slate-600">{hint}</span> : null}
    </>
  );
  const cls = cn(
    "min-w-0 rounded-2xl px-4 py-3 text-left",
    active ? "bg-primary/[0.04] ring-1 ring-primary/15" : "",
    onClick &&
      "hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-secondary"
  );
  return onClick ? (
    <button type="button" onClick={onClick} className={cls} aria-pressed={active}>
      {body}
    </button>
  ) : (
    <div className={cls}>{body}</div>
  );
}

export function Panel({
  title,
  aside,
  children,
  className,
}: {
  title?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("min-w-0 rounded-3xl border border-primary/10 bg-white", className)}>
      {title || aside ? (
        <div className="flex items-center justify-between gap-3 px-5 pt-5 sm:px-6">
          {title ? (
            <h2 className="text-base font-bold tracking-tight text-primary">{title}</h2>
          ) : (
            <span />
          )}
          {aside}
        </div>
      ) : null}
      <div className="px-5 py-5 sm:px-6">{children}</div>
    </section>
  );
}

/** One quiet status word. Use at most one per row; red only for money or blockers. */
export function Pill({
  children,
  tone = "slate",
}: {
  children: ReactNode;
  tone?: "slate" | "red" | "amber" | "green" | "navy";
}) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    red: "bg-red-50 text-red-700",
    amber: "bg-amber-50 text-amber-800",
    green: "bg-emerald-50 text-emerald-800",
    navy: "bg-primary text-white",
  } as const;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap",
        tones[tone]
      )}
    >
      {children}
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <span aria-hidden className={cn("block animate-pulse rounded-lg bg-slate-100", className)} />
  );
}

export function SkeletonRows({ rows = 5, label = "Loading" }: { rows?: number; label?: string }) {
  return (
    <div role="status" aria-busy="true" aria-label={label} className="space-y-3 py-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5 w-1/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <Skeleton className="h-4 w-16" />
        </div>
      ))}
      <span className="sr-only">{label}…</span>
    </div>
  );
}

/** Designed empty state: icon, one sentence, optional single action. */
export function Empty({
  icon,
  title,
  hint,
  action,
}: {
  icon?: ReactNode;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      {icon ? (
        <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/[0.05] text-primary">
          {icon}
        </span>
      ) : null}
      <p className="text-base font-bold text-primary">{title}</p>
      {hint ? <p className="mt-1 max-w-sm text-sm text-slate-600">{hint}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export type MenuItem = {
  label: string;
  onSelect: () => void;
  tone?: "danger";
  disabled?: boolean;
  hint?: string;
};

/** Accessible "⋯" menu: secondary actions live here, not as more buttons. */
export function ActionMenu({
  items,
  label = "More actions",
  trigger,
  align = "right",
}: {
  items: MenuItem[];
  label?: string;
  trigger?: ReactNode;
  align?: "left" | "right";
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const id = useId();
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    ref.current?.querySelector<HTMLButtonElement>('[role="menuitem"]:not([disabled])')?.focus();
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);
  const visible = items.filter(Boolean);
  if (!visible.length) return null;
  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={id}
        aria-label={trigger ? undefined : label}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-primary/15 text-sm font-semibold text-primary hover:bg-slate-50",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary",
          trigger ? "px-4" : "w-11"
        )}
      >
        {trigger ?? <MoreHorizontal className="h-5 w-5" aria-hidden />}
      </button>
      {open && (
        <div
          id={id}
          role="menu"
          aria-label={label}
          onKeyDown={(e) => {
            if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
            e.preventDefault();
            const els = [
              ...(ref.current?.querySelectorAll<HTMLButtonElement>(
                '[role="menuitem"]:not([disabled])'
              ) ?? []),
            ];
            const i = els.indexOf(document.activeElement as HTMLButtonElement);
            const next =
              e.key === "ArrowDown" ? (i + 1) % els.length : (i - 1 + els.length) % els.length;
            els[next]?.focus();
          }}
          className={cn(
            "absolute z-30 mt-2 min-w-[14rem] overflow-hidden rounded-2xl border border-primary/10 bg-white py-1.5 shadow-xl",
            align === "right" ? "right-0" : "left-0"
          )}
        >
          {visible.map((it) => (
            <button
              key={it.label}
              type="button"
              role="menuitem"
              disabled={it.disabled}
              onClick={() => {
                setOpen(false);
                it.onSelect();
              }}
              className={cn(
                "block min-h-11 w-full px-4 py-2 text-left text-sm font-medium focus:bg-slate-50 focus:outline-none disabled:opacity-50",
                it.tone === "danger"
                  ? "text-red-700 hover:bg-red-50"
                  : "text-primary hover:bg-slate-50"
              )}
            >
              {it.label}
              {it.hint ? (
                <span className="block text-xs font-normal text-slate-600">{it.hint}</span>
              ) : null}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** Accessible dialog: role=dialog, Esc closes, focus moves in and returns; bottom sheet under 640px. */
export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children?: ReactNode;
  footer?: ReactNode;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descId = useId();
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    const first = panel.current?.querySelector<HTMLElement>(
      "input, select, textarea, button:not([data-close])"
    );
    (first ?? panel.current)?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && panel.current) {
        const els = [
          ...panel.current.querySelectorAll<HTMLElement>(
            "a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])"
          ),
        ];
        if (!els.length) return;
        const [a, b] = [els[0], els[els.length - 1]];
        if (e.shiftKey && document.activeElement === a) {
          e.preventDefault();
          b.focus();
        } else if (!e.shiftKey && document.activeElement === b) {
          e.preventDefault();
          a.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
      prev?.focus?.();
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4">
      <div
        className="absolute inset-0 bg-primary/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descId : undefined}
        tabIndex={-1}
        className="relative max-h-[92dvh] w-full overflow-y-auto rounded-t-3xl bg-white shadow-2xl outline-none sm:max-w-lg sm:rounded-3xl"
      >
        <div className="flex items-start justify-between gap-4 px-6 pt-6">
          <div>
            <h2 id={titleId} className="text-xl font-extrabold tracking-tight text-primary">
              {title}
            </h2>
            {description ? (
              <p id={descId} className="mt-1 text-sm text-slate-600">
                {description}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            data-close
            onClick={onClose}
            aria-label="Close"
            className="-mt-1 -mr-2 inline-flex h-11 w-11 items-center justify-center rounded-full text-slate-600 hover:bg-slate-100"
          >
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>
        {children ? <div className="space-y-4 px-6 py-5">{children}</div> : <div className="h-4" />}
        {footer ? (
          <div className="flex flex-col-reverse gap-2 border-t border-primary/10 px-6 py-4 sm:flex-row sm:justify-end">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function FieldLabel({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-semibold text-primary">{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-xs text-slate-600">{hint}</span> : null}
    </label>
  );
}

const inputCore =
  "block min-h-11 w-full border border-primary/15 bg-white text-sm text-primary placeholder:text-slate-500 focus:border-secondary focus:ring-2 focus:ring-secondary/20 focus:outline-none";
export const inputClass = `${inputCore} rounded-xl px-3.5`;
export const pillInputClass = `${inputCore} rounded-full px-4`;
export const searchInputClass = `${inputCore} rounded-full pr-10 pl-10`;

/** "Reason" prompt as a real dialog (replaces window.prompt). */
export function ReasonDialog({
  open,
  title,
  description,
  confirm,
  tone = "default",
  busy,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  title: string;
  description?: string;
  confirm: string;
  tone?: "default" | "danger";
  busy?: boolean;
  onCancel: () => void;
  onConfirm: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  useEffect(() => {
    if (open) setReason("");
  }, [open]);
  return (
    <Dialog
      open={open}
      onClose={onCancel}
      title={title}
      description={description}
      footer={
        <>
          <QuietButton onClick={onCancel}>Cancel</QuietButton>
          <PrimaryAction
            disabled={!reason.trim() || busy}
            onClick={() => onConfirm(reason.trim())}
            tone={tone === "danger" ? "danger" : "accent"}
          >
            {busy ? "Working…" : confirm}
          </PrimaryAction>
        </>
      }
    >
      <FieldLabel label="Reason" hint="Saved to the change history on each account.">
        <input
          className={inputClass}
          value={reason}
          maxLength={255}
          onChange={(e) => setReason(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && reason.trim() && !busy) onConfirm(reason.trim());
          }}
        />
      </FieldLabel>
    </Dialog>
  );
}

/** Small keyboard-hint chip. */
export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="inline-flex min-w-5 items-center justify-center rounded-md border border-primary/15 bg-white px-1.5 font-sans text-[11px] font-semibold text-primary">
      {children}
    </kbd>
  );
}
