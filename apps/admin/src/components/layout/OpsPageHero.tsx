"use client";

import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@porterchain/ui/utils";

type Props = {
  icon?: LucideIcon;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
  children?: ReactNode;
};

/**
 * Shared first-viewport chrome for Control Tower, Orders, and Booking Drafts.
 * One composition: icon + title + short lede + actions.
 */
export default function OpsPageHero({
  icon: Icon,
  title,
  description,
  actions,
  className,
  children,
}: Props) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-primary/10 bg-gradient-to-br from-white via-white to-secondary/5 px-4 py-5 shadow-sm sm:px-6 sm:py-5",
        className
      )}
    >
      <div className="relative z-10 flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          {Icon ? (
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-secondary/10">
              <Icon className="h-5 w-5 text-secondary" aria-hidden />
            </div>
          ) : null}
          <div className="min-w-0">
            {typeof title === "string" ? (
              <h1 className="text-2xl font-bold tracking-tight text-primary">{title}</h1>
            ) : (
              title
            )}
            {description ? (
              typeof description === "string" ? (
                <p className="mt-1 max-w-2xl text-sm text-muted">{description}</p>
              ) : (
                description
              )
            ) : null}
          </div>
        </div>
        {actions ? (
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">{actions}</div>
        ) : null}
      </div>
      {children ? <div className="relative z-10 mt-4">{children}</div> : null}
    </div>
  );
}
