"use client";

import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { ChevronDown, LogIn, LogOut, type LucideIcon } from "lucide-react";
import { HeaderDropdown } from "./header-dropdown";
import { cn } from "./utils";

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

export function AccountAvatar({
  name,
  src,
  size = "sm",
  soft = false,
}: {
  name: string;
  src?: string | null;
  size?: "sm" | "lg";
  /** Light secondary tint instead of the solid brand circle. */
  soft?: boolean;
}) {
  const box = size === "lg" ? "h-12 w-12 shadow-md" : "h-8 w-8";
  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={src} alt="" className={cn(box, "rounded-full object-cover ring-2 ring-white")} />
    );
  }
  return (
    <span
      className={cn(
        box,
        "flex items-center justify-center rounded-full font-bold",
        size === "lg" ? "text-sm" : "text-xs",
        soft ? "bg-secondary/10 text-secondary" : "bg-secondary text-white"
      )}
    >
      {initials(name)}
    </span>
  );
}

export type AccountMenuProps = {
  name: string;
  email: string;
  avatar?: string | null;
  softAvatar?: boolean;
  /** Second line next to the avatar in the header button (company, online status…). */
  triggerSubtitle?: string;
  /** Badges / extra rows under the name in the panel header. */
  badges?: ReactNode;
  headerExtra?: ReactNode;
  /** Bigger avatar + gradient header (portal accounts) vs a compact staff header. */
  richHeader?: boolean;
  footer: ReactNode;
  children: ReactNode;
};

/** Header account dropdown shared by the web portals; each portal supplies items and sign-out. */
export function AccountMenu({
  name,
  email,
  avatar,
  softAvatar,
  triggerSubtitle,
  badges,
  headerExtra,
  richHeader = true,
  footer,
  children,
}: AccountMenuProps) {
  return (
    <HeaderDropdown
      align="right"
      width="md"
      trigger={({ open, triggerProps }) => (
        <button
          type="button"
          {...triggerProps}
          aria-label="Account menu"
          className={cn(
            "flex h-10 max-w-[12rem] items-center gap-2 rounded-full border border-primary/10 bg-white py-1 pl-1 pr-2.5 shadow-sm transition hover:bg-gray-bg",
            open && "border-secondary/30 ring-2 ring-secondary/20"
          )}
        >
          <AccountAvatar name={name || email} src={avatar} soft={softAvatar} />
          {triggerSubtitle !== undefined ? (
            <span className="hidden min-w-0 flex-1 text-left sm:block">
              <span className="block truncate text-xs font-semibold text-primary">
                {name.split(" ")[0]}
              </span>
              <span className="block truncate text-[10px] text-muted">{triggerSubtitle}</span>
            </span>
          ) : (
            <span className="hidden min-w-0 flex-1 truncate text-left text-sm font-medium text-primary sm:block">
              {name}
            </span>
          )}
          <ChevronDown
            className={cn("h-4 w-4 shrink-0 text-muted transition", open && "rotate-180")}
          />
        </button>
      )}
    >
      <div
        className={cn(
          "border-b border-primary/8 px-4",
          richHeader ? "bg-gradient-to-br from-slate-50 to-white py-4" : "py-3"
        )}
      >
        <div className="flex items-center gap-3">
          {richHeader ? <AccountAvatar name={name} src={avatar} size="lg" /> : null}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-primary">{name}</p>
            <p className="truncate text-xs text-muted">{email}</p>
            {badges ? <div className="mt-1.5 flex flex-wrap gap-1.5">{badges}</div> : null}
          </div>
        </div>
        {headerExtra}
      </div>
      <div className="p-1.5">{children}</div>
      <div className="border-t border-primary/8 bg-slate-50/80 p-2">{footer}</div>
    </HeaderDropdown>
  );
}

export function AccountBadge({
  children,
  tone = "secondary",
}: {
  children: ReactNode;
  tone?: "secondary" | "neutral" | "success";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide",
        tone === "secondary" && "bg-secondary/10 text-secondary",
        tone === "neutral" && "bg-gray-100 text-gray-600",
        tone === "success" && "bg-emerald-100 text-emerald-800"
      )}
    >
      {children}
    </span>
  );
}

function ItemBody({
  icon: Icon,
  label,
  hint,
  danger,
}: {
  icon: LucideIcon;
  label: ReactNode;
  hint: ReactNode;
  danger?: boolean;
}) {
  return (
    <>
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", danger ? "text-red-600" : "text-secondary")} />
      <span className="min-w-0 text-left">
        <span className={cn("block text-sm font-medium", danger ? "text-red-700" : "text-primary")}>
          {label}
        </span>
        <span className="block text-xs text-muted">{hint}</span>
      </span>
    </>
  );
}

const ITEM_CLASS =
  "flex w-full items-start gap-3 rounded-xl px-3 py-2.5 transition hover:bg-gray-bg disabled:opacity-50";

export function AccountMenuLink({
  href,
  icon,
  label,
  hint,
  danger,
}: {
  href: string;
  icon: LucideIcon;
  label: string;
  hint: string;
  danger?: boolean;
}) {
  return (
    <Link href={href} role="menuitem" className={cn(ITEM_CLASS, danger && "hover:bg-red-50")}>
      <ItemBody icon={icon} label={label} hint={hint} danger={danger} />
    </Link>
  );
}

export function AccountMenuButton({
  icon,
  label,
  hint,
  ...props
}: { icon: LucideIcon; label: ReactNode; hint: ReactNode } & Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  "children"
>) {
  return (
    <button type="button" {...props} className={ITEM_CLASS}>
      <ItemBody icon={icon} label={label} hint={hint} />
    </button>
  );
}

/** Red "Sign out" button; extra props let the auth <SignOutButton> wrap it. */
export function AccountSignOutButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className="flex w-full items-center justify-center gap-2 rounded-xl border border-red-200 bg-white px-4 py-2.5 text-sm font-semibold text-red-600 shadow-sm transition hover:bg-red-50"
    >
      <LogOut className="h-4 w-4" />
      Sign out
    </button>
  );
}

export function AccountSignInLink({ href, primary = false }: { href: string; primary?: boolean }) {
  return (
    <Link
      href={href}
      className={cn(
        "flex h-10 items-center gap-2 rounded-full px-4 text-sm shadow-sm",
        primary
          ? "bg-secondary font-semibold text-white hover:bg-secondary/90"
          : "border border-primary/10 bg-white font-medium text-primary hover:bg-gray-bg"
      )}
    >
      <LogIn className={cn("h-4 w-4", !primary && "text-secondary")} />
      Sign in
    </Link>
  );
}
