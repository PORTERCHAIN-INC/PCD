"use client";

import type { ReactNode } from "react";
import { cn } from "@porterchain/ui/utils";

type Props = {
  children: ReactNode;
  className?: string;
  /** Page title row — keep actions on the right */
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
};

/**
 * Full-viewport ops page chrome. Every (ops) screen should use this (or sit under
 * AdminShell’s fluid Container) so tables/KPIs span the monitor.
 */
export default function AdminPage({ children, className, title, description, actions }: Props) {
  const hasHeader = title != null || description != null || actions != null;
  return (
    <div className={cn("admin-page w-full min-w-0 max-w-none space-y-6", className)}>
      {hasHeader ? (
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            {title ? (
              typeof title === "string" ? (
                <h1 className="text-2xl font-bold tracking-tight text-primary">{title}</h1>
              ) : (
                title
              )
            ) : null}
            {description ? (
              typeof description === "string" ? (
                <p className="mt-1 text-sm text-muted">{description}</p>
              ) : (
                description
              )
            ) : null}
          </div>
          {actions ? (
            <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
          ) : null}
        </div>
      ) : null}
      {children}
    </div>
  );
}
