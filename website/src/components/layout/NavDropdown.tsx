"use client";

import { useEffect, useId, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import type { NavbarChildLink } from "@/data/navbar-navigation";

interface NavDropdownProps {
  label: string;
  href?: string;
  items: NavbarChildLink[];
  getChildLabel: (id: string) => string;
  linkClass: (active?: boolean) => string;
  pathname: string;
  navLight: boolean;
  onNavigate?: () => void;
  /** Mobile drawer on brand bar — light text instead of primary */
  mobileOnDarkBar?: boolean;
  /** Desktop inline nav vs mobile stacked menu */
  variant?: "desktop" | "mobile";
}

export default function NavDropdown({
  label,
  href,
  items,
  getChildLabel,
  linkClass,
  pathname,
  navLight,
  onNavigate,
  mobileOnDarkBar = false,
  variant = "desktop",
}: NavDropdownProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  const childActive = items.some(
    (child) => pathname === child.href || pathname.startsWith(`${child.href}/`)
  );
  const parentActive = href ? pathname === href || pathname.startsWith(`${href}/`) : false;
  const active = childActive || parentActive;

  useEffect(() => {
    if (variant !== "desktop") return;
    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [variant]);

  if (variant === "mobile") {
    return (
      <div className="py-1">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className={cn(
            "flex w-full items-center justify-between px-4 py-3 text-sm font-medium rounded-xl",
            mobileOnDarkBar
              ? "text-white/90 hover:bg-white/10 hover:text-white"
              : "text-primary hover:bg-gray-bg"
          )}
          aria-expanded={open}
        >
          {label}
          <ChevronDown className={cn("w-4 h-4 transition-transform", open && "rotate-180")} />
        </button>
        {open && (
          <div className="mt-1 space-y-0.5 pl-2">
            {items.map((child) => (
              <Link
                key={child.id}
                href={child.href}
                onClick={onNavigate}
                className={cn(
                  "block px-4 py-2.5 text-sm rounded-xl",
                  mobileOnDarkBar
                    ? "text-white/75 hover:bg-white/10 hover:text-white"
                    : "text-primary/80 hover:bg-gray-bg hover:text-primary"
                )}
              >
                {getChildLabel(child.id)}
              </Link>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      ref={rootRef}
      className="relative"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      {href ? (
        <Link
          href={href}
          className={cn(linkClass(active), "inline-flex items-center gap-1")}
          aria-haspopup="menu"
          aria-expanded={open}
          aria-controls={menuId}
          onFocus={() => setOpen(true)}
        >
          {label}
          <ChevronDown
            className={cn("w-3.5 h-3.5 opacity-70 transition-transform", open && "rotate-180")}
          />
        </Link>
      ) : (
        <button
          type="button"
          className={cn(linkClass(active), "inline-flex items-center gap-1")}
          aria-haspopup="menu"
          aria-expanded={open}
          aria-controls={menuId}
          onClick={() => setOpen((value) => !value)}
          onFocus={() => setOpen(true)}
        >
          {label}
          <ChevronDown
            className={cn("w-3.5 h-3.5 opacity-70 transition-transform", open && "rotate-180")}
          />
        </button>
      )}

      {open && (
        <div
          id={menuId}
          role="menu"
          className={cn(
            "absolute left-0 top-full z-50 mt-1 min-w-[15rem] rounded-xl border py-1.5 shadow-lg",
            navLight
              ? "border-primary/[0.08] bg-white shadow-primary/10"
              : "border-white/15 bg-primary/95 backdrop-blur-xl shadow-black/20"
          )}
        >
          {items.map((child) => {
            const isActive = pathname === child.href || pathname.startsWith(`${child.href}/`);
            return (
              <Link
                key={child.id}
                href={child.href}
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  onNavigate?.();
                }}
                className={cn(
                  "block px-4 py-2.5 text-sm transition-colors",
                  navLight
                    ? isActive
                      ? "text-secondary bg-secondary/5"
                      : "text-primary/80 hover:bg-gray-bg hover:text-primary"
                    : isActive
                      ? "text-white bg-white/10"
                      : "text-white/80 hover:bg-white/10 hover:text-white"
                )}
              >
                {getChildLabel(child.id)}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
