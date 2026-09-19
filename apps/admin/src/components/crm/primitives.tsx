"use client";

import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { initials } from "@/lib/crmFormat";

const TONES: Record<string, string> = {
  blue: "bg-blue-50 text-blue-700 ring-blue-600/20",
  sky: "bg-sky-50 text-sky-700 ring-sky-600/20",
  green: "bg-green-50 text-green-700 ring-green-600/20",
  red: "bg-red-50 text-red-700 ring-red-600/20",
  amber: "bg-amber-50 text-amber-700 ring-amber-600/20",
  violet: "bg-violet-50 text-violet-700 ring-violet-600/20",
  teal: "bg-teal-50 text-teal-700 ring-teal-600/20",
  slate: "bg-slate-100 text-slate-600 ring-slate-500/20",
};

export function Badge({
  children,
  tone = "slate",
  className,
}: {
  children: ReactNode;
  tone?: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        TONES[tone] ?? TONES.slate,
        className
      )}
    >
      {children}
    </span>
  );
}

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "outline";

const BTN: Record<ButtonVariant, string> = {
  primary: "bg-secondary text-white hover:bg-secondary/90",
  secondary: "bg-primary text-white hover:bg-primary/90",
  ghost: "text-primary/70 hover:bg-gray-bg",
  danger: "bg-red-600 text-white hover:bg-red-700",
  outline: "border border-primary/15 bg-white text-primary hover:bg-gray-bg",
};

export function Button({
  children,
  variant = "primary",
  className,
  type = "button",
  disabled,
  onClick,
  title,
}: {
  children: ReactNode;
  variant?: ButtonVariant;
  className?: string;
  type?: "button" | "submit";
  disabled?: boolean;
  onClick?: () => void;
  title?: string;
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      title={title}
      className={cn(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        BTN[variant],
        className
      )}
    >
      {children}
    </button>
  );
}

export function Avatar({
  name,
  className,
}: {
  name: string | null | undefined;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-secondary/10 text-xs font-semibold text-secondary",
        className
      )}
    >
      {initials(name)}
    </span>
  );
}

export function SectionCard({
  title,
  icon,
  action,
  children,
  className,
}: {
  title?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "min-w-0 overflow-hidden rounded-2xl border border-primary/10 bg-white",
        className
      )}
    >
      {(title || action) && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-primary/10 px-4 py-3.5 sm:px-5">
          <h2 className="flex min-w-0 items-center gap-2 text-sm font-semibold text-primary">
            {icon}
            {title}
          </h2>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 px-6 py-16 text-center">
      <p className="text-sm font-medium text-primary">{title}</p>
      {hint && <p className="max-w-sm text-sm text-muted">{hint}</p>}
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 px-6 py-16 text-sm text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-secondary/30 border-t-secondary" />
      {label}
    </div>
  );
}

export function Field({
  label,
  children,
  hint,
  className,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
  className?: string;
}) {
  return (
    <label className={cn("block space-y-1", className)}>
      <span className="text-xs font-medium text-primary/70">{label}</span>
      {children}
      {hint && <span className="block text-xs text-muted">{hint}</span>}
    </label>
  );
}

const FIELD_CLASS =
  "w-full rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm text-primary outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/20";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn(FIELD_CLASS, props.className)} />;
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cn(FIELD_CLASS, "min-h-[80px]", props.className)} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cn(FIELD_CLASS, "appearance-none", props.className)} />;
}

export function Drawer({
  open,
  onClose,
  title,
  children,
  footer,
  width = "max-w-xl",
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  width?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-primary/30 backdrop-blur-sm" onClick={onClose} />
      <div className={cn("relative flex h-full w-full flex-col bg-white shadow-2xl", width)}>
        <div className="flex items-center justify-between border-b border-primary/10 px-5 py-4">
          <div className="text-base font-semibold text-primary">{title}</div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-muted hover:bg-gray-bg">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-5">{children}</div>
        {footer && (
          <div className="flex items-center justify-end gap-2 border-t border-primary/10 px-5 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  panelClassName,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  panelClassName?: string;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-primary/30 backdrop-blur-sm" onClick={onClose} />
      <div
        className={cn("relative w-full max-w-lg rounded-2xl bg-white shadow-2xl", panelClassName)}
      >
        <div className="flex items-center justify-between border-b border-primary/10 px-5 py-4">
          <div className="text-base font-semibold text-primary">{title}</div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-muted hover:bg-gray-bg">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="px-5 py-5">{children}</div>
        {footer && (
          <div className="flex items-center justify-end gap-2 border-t border-primary/10 px-5 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
