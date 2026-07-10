"use client";

import { useEffect, useId, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  BookOpen,
  Briefcase,
  Building2,
  ChevronDown,
  CircleHelp,
  Code2,
  HardHat,
  HeartPulse,
  LayoutGrid,
  Mail,
  MapPin,
  Newspaper,
  PackageSearch,
  Route,
  Server,
  Truck,
  Users,
  UtensilsCrossed,
  Warehouse,
  type LucideIcon,
} from "lucide-react";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import type { NavbarChildLink } from "@/data/navbar-navigation";

const CHILD_ICONS: Record<string, LucideIcon> = {
  overview: LayoutGrid,
  wholesale: Warehouse,
  medical: HeartPulse,
  foodBeverage: UtensilsCrossed,
  construction: HardHat,
  industries: Building2,
  serviceAreas: MapPin,
  about: Users,
  careers: Briefcase,
  contact: Mail,
  vehiclePartner: Truck,
  blog: Newspaper,
  faq: CircleHelp,
  guides: BookOpen,
  track: PackageSearch,
  howItWorks: Route,
  platform: Server,
  developers: Code2,
};

interface NavDropdownProps {
  menuId: string;
  label: string;
  href?: string;
  items: NavbarChildLink[];
  getChildLabel: (id: string) => string;
  getChildDescription?: (id: string) => string;
  linkClass: (active?: boolean) => string;
  pathname: string;
  navLight: boolean;
  onNavigate?: () => void;
  mobileOnDarkBar?: boolean;
  variant?: "desktop" | "mobile";
}

export default function NavDropdown({
  menuId,
  label,
  href,
  items,
  getChildLabel,
  getChildDescription,
  linkClass,
  pathname,
  navLight,
  onNavigate,
  mobileOnDarkBar = false,
  variant = "desktop",
}: NavDropdownProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuIdAttr = useId();
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const childActive = items.some(
    (child) => pathname === child.href || pathname.startsWith(`${child.href}/`)
  );
  const parentActive = href ? pathname === href || pathname.startsWith(`${href}/`) : false;
  const active = childActive || parentActive;

  const clearCloseTimer = () => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  const scheduleClose = () => {
    clearCloseTimer();
    closeTimer.current = setTimeout(() => setOpen(false), 120);
  };

  useEffect(() => {
    if (variant !== "desktop") return;
    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
      clearCloseTimer();
    };
  }, [variant]);

  if (variant === "mobile") {
    return (
      <div className="py-0.5">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className={cn(
            "flex w-full items-center justify-between gap-3 px-4 py-3 text-sm font-medium rounded-xl transition-colors",
            mobileOnDarkBar ? "text-white/90 hover:bg-white/10" : "text-primary hover:bg-gray-bg"
          )}
          aria-expanded={open}
        >
          <span className="flex items-center gap-2.5">
            <span
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-lg",
                mobileOnDarkBar ? "bg-white/10" : "bg-secondary/10"
              )}
            >
              <LayoutGrid
                className={cn("h-4 w-4", mobileOnDarkBar ? "text-white" : "text-secondary")}
                aria-hidden
              />
            </span>
            {label}
          </span>
          <ChevronDown
            className={cn(
              "h-4 w-4 shrink-0 transition-transform duration-200",
              open && "rotate-180"
            )}
          />
        </button>
        <AnimatePresence initial={false}>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="mt-1 space-y-0.5 pl-3 pr-1 pb-1">
                {items.map((child) => {
                  const Icon = CHILD_ICONS[child.id] ?? LayoutGrid;
                  const isActive = pathname === child.href || pathname.startsWith(`${child.href}/`);
                  const description = getChildDescription?.(child.id);
                  return (
                    <Link
                      key={child.id}
                      href={child.href}
                      onClick={onNavigate}
                      className={cn(
                        "flex items-start gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors",
                        mobileOnDarkBar
                          ? isActive
                            ? "bg-white/15 text-white"
                            : "text-white/75 hover:bg-white/10 hover:text-white"
                          : isActive
                            ? "bg-secondary/10 text-secondary"
                            : "text-primary/80 hover:bg-gray-bg hover:text-primary"
                      )}
                    >
                      <span
                        className={cn(
                          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                          mobileOnDarkBar ? "bg-white/10" : "bg-secondary/8"
                        )}
                      >
                        <Icon
                          className={cn(
                            "h-4 w-4",
                            mobileOnDarkBar ? "text-white/90" : "text-secondary"
                          )}
                          aria-hidden
                        />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block font-medium leading-snug">
                          {getChildLabel(child.id)}
                        </span>
                        {description && (
                          <span
                            className={cn(
                              "mt-0.5 block text-xs leading-snug line-clamp-2",
                              mobileOnDarkBar ? "text-white/55" : "text-muted"
                            )}
                          >
                            {description}
                          </span>
                        )}
                      </span>
                    </Link>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  const panelItems = href ? items.filter((child) => child.href !== href) : items;
  const hasDescriptions = Boolean(getChildDescription);
  const useGrid = !hasDescriptions && panelItems.length > 4;
  const alignRight = menuId === "resources" || menuId === "company";

  return (
    <div
      ref={rootRef}
      className="relative"
      onMouseEnter={() => {
        clearCloseTimer();
        setOpen(true);
      }}
      onMouseLeave={scheduleClose}
    >
      <button
        type="button"
        className={cn(linkClass(active), "inline-flex items-center gap-1.5")}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuIdAttr}
        onClick={() => setOpen((value) => !value)}
      >
        {label}
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 opacity-70 transition-transform duration-200",
            open && "rotate-180"
          )}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.98 }}
            transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
            className={cn("absolute top-full z-50 pt-2", alignRight ? "right-0" : "left-0")}
            onMouseEnter={clearCloseTimer}
            onMouseLeave={scheduleClose}
          >
            <div
              id={menuIdAttr}
              role="menu"
              className={cn(
                "overflow-hidden rounded-2xl border border-primary/8 bg-white/95 p-2 shadow-premium backdrop-blur-xl",
                hasDescriptions
                  ? menuId === "solutions"
                    ? "w-[min(24rem,calc(100vw-2rem))]"
                    : "w-[min(20rem,calc(100vw-2rem))]"
                  : useGrid
                    ? "w-[min(28rem,calc(100vw-2rem))]"
                    : "w-[17.5rem]"
              )}
            >
              {href && (
                <Link
                  href={href}
                  role="none"
                  onClick={() => setOpen(false)}
                  className="mb-1 flex items-center justify-between rounded-xl px-3 py-2.5 text-sm font-semibold text-secondary hover:bg-secondary/5 transition-colors"
                >
                  {label}
                  <span className="text-secondary/60" aria-hidden>
                    →
                  </span>
                </Link>
              )}

              {href && panelItems.length > 0 && (
                <div className="mx-2 mb-1 border-t border-primary/6" aria-hidden />
              )}

              <div className={cn(useGrid && "grid grid-cols-2 gap-0.5")}>
                {panelItems.map((child) => {
                  const Icon = CHILD_ICONS[child.id] ?? LayoutGrid;
                  const isActive = pathname === child.href || pathname.startsWith(`${child.href}/`);
                  const description = getChildDescription?.(child.id);
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
                        "group flex items-start gap-3 rounded-xl p-3 transition-colors",
                        isActive
                          ? "bg-secondary/10 text-secondary"
                          : "text-primary hover:bg-gray-bg"
                      )}
                    >
                      <span
                        className={cn(
                          "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors",
                          isActive
                            ? "bg-secondary/15 text-secondary"
                            : "bg-gray-bg text-primary/70 group-hover:bg-secondary/10 group-hover:text-secondary"
                        )}
                      >
                        <Icon className="h-4 w-4" aria-hidden />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-medium leading-snug">
                          {getChildLabel(child.id)}
                        </span>
                        {description && (
                          <span className="mt-1 block text-xs leading-snug text-muted line-clamp-2">
                            {description}
                          </span>
                        )}
                      </span>
                    </Link>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
