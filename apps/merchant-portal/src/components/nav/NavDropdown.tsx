"use client";

import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

type PanelRender = (props: { close: () => void }) => ReactNode;

type Props = {
  trigger: (props: {
    open: boolean;
    toggle: () => void;
    triggerProps: { onClick: () => void; "aria-expanded": boolean; "aria-haspopup": boolean };
  }) => ReactNode;
  children: ReactNode | PanelRender;
  align?: "left" | "right";
  width?: "sm" | "md" | "lg" | "xl";
  className?: string;
};

const WIDTH = { sm: 224, md: 288, lg: 320, xl: 420 };

export default function NavDropdown({
  trigger,
  children,
  align = "left",
  width = "md",
  className,
}: Props) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0, width: WIDTH[width] });
  const triggerRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  const close = useCallback(() => setOpen(false), []);
  const toggle = useCallback(() => setOpen((v) => !v), []);

  useEffect(() => {
    close();
  }, [pathname, close]);

  const updatePosition = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const panelWidth = Math.min(WIDTH[width], window.innerWidth - 16);
    let left = align === "right" ? rect.right - panelWidth : rect.left;
    left = Math.max(8, Math.min(left, window.innerWidth - panelWidth - 8));
    setPosition({ top: rect.bottom + 6, left, width: panelWidth });
  }, [align, width]);

  useEffect(() => {
    if (!open) return;
    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open, updatePosition]);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      const target = e.target as Node;
      if (triggerRef.current?.contains(target) || panelRef.current?.contains(target)) return;
      close();
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, close]);

  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    if (!panel) return;
    function onClick(e: MouseEvent) {
      const el = e.target as HTMLElement | null;
      if (el?.closest("a[href]")) close();
    }
    panel.addEventListener("click", onClick);
    return () => panel.removeEventListener("click", onClick);
  }, [open, close]);

  const panelContent = typeof children === "function" ? children({ close }) : children;

  const panel =
    open && typeof document !== "undefined"
      ? createPortal(
          <div
            ref={panelRef}
            id={menuId}
            role="menu"
            style={{ top: position.top, left: position.left, width: position.width }}
            className={cn(
              "fixed z-[9999] overflow-hidden rounded-xl border border-primary/10 bg-white shadow-2xl shadow-primary/15",
              className
            )}
          >
            {panelContent}
          </div>,
          document.body
        )
      : null;

  return (
    <>
      <div ref={triggerRef} className="inline-flex">
        {trigger({
          open,
          toggle,
          triggerProps: { onClick: toggle, "aria-expanded": open, "aria-haspopup": true },
        })}
      </div>
      {panel}
    </>
  );
}
