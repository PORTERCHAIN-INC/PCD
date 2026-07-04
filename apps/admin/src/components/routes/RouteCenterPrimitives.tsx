"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { ArrowRight, Route } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { Badge, Button, EmptyState, SectionCard } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";
import type { RoutePlan } from "@/lib/route-center";

export function RouteCardBody({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn("p-5", className)}>{children}</div>;
}

export function RouteSectionCard({
  title,
  description,
  action,
  children,
  className,
}: {
  title?: ReactNode;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <SectionCard
      title={
        description ? (
          <span>
            {title}
            <span className="mt-0.5 block text-xs font-normal text-muted">{description}</span>
          </span>
        ) : (
          title
        )
      }
      action={action}
      className={className}
    >
      <RouteCardBody>{children}</RouteCardBody>
    </SectionCard>
  );
}

export function routeStatusTone(status: string): string {
  switch (status) {
    case "completed":
    case "dispatched":
    case "active":
      return "green";
    case "optimized":
    case "planned":
      return "blue";
    case "waiting":
    case "pending":
      return "amber";
    case "cancelled":
    case "failed":
      return "red";
    default:
      return "slate";
  }
}

export function RouteStatusBadge({ status }: { status: string }) {
  return <Badge tone={routeStatusTone(status)}>{titleCase(status)}</Badge>;
}

export function RouteKpiTile({
  label,
  value,
  icon: Icon,
  href,
  hint,
  tone = "default",
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  href?: string;
  hint?: string;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  const toneClass =
    tone === "success"
      ? "border-green-200/80 bg-green-50/50"
      : tone === "warning"
        ? "border-amber-200/80 bg-amber-50/50"
        : tone === "danger"
          ? "border-red-200/80 bg-red-50/50"
          : "border-primary/10 bg-white";

  const body = (
    <div
      className={cn(
        "group rounded-2xl border p-4 transition-all",
        toneClass,
        href && "hover:border-secondary/30 hover:shadow-sm"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted">{label}</p>
          <p className="mt-1.5 text-2xl font-bold tracking-tight text-primary">{value}</p>
          {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
        </div>
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-secondary/10 text-secondary">
          <Icon className="h-4 w-4" />
        </span>
      </div>
      {href && (
        <p className="mt-2 flex items-center gap-1 text-xs font-medium text-secondary opacity-0 transition-opacity group-hover:opacity-100">
          View <ArrowRight className="h-3 w-3" />
        </p>
      )}
    </div>
  );

  return href ? (
    <Link href={href} className="block">
      {body}
    </Link>
  ) : (
    body
  );
}

export function RoutePlanRow({
  plan,
  meta,
  actions,
}: {
  plan: RoutePlan;
  meta?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/10 bg-gray-bg/30 p-4 transition-colors hover:border-secondary/20 hover:bg-white">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={`/routes/${plan.id}`}
            className="font-semibold text-primary hover:text-secondary hover:underline"
          >
            {plan.name}
          </Link>
          <RouteStatusBadge status={plan.status} />
          {plan.requires_approval ? <Badge tone="amber">Approval required</Badge> : null}
        </div>
        <p className="mt-1 text-xs text-muted">
          {plan.order_ids.length} orders · {plan.stops.length} stops · {titleCase(plan.strategy)}
        </p>
        {meta}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function RoutePlanList({
  plans,
  emptyTitle,
  emptyHint,
  renderActions,
  renderMeta,
}: {
  plans: RoutePlan[];
  emptyTitle: string;
  emptyHint?: string;
  renderActions?: (plan: RoutePlan) => ReactNode;
  renderMeta?: (plan: RoutePlan) => ReactNode;
}) {
  if (plans.length === 0) {
    return (
      <RouteEmptyState
        title={emptyTitle}
        hint={emptyHint ?? "Create a route plan in Route Builder or import from a template."}
      />
    );
  }

  return (
    <div className="space-y-3">
      {plans.map((plan) => (
        <RoutePlanRow
          key={plan.id}
          plan={plan}
          meta={renderMeta?.(plan)}
          actions={
            renderActions?.(plan) ?? (
              <Link href={`/routes/${plan.id}`}>
                <Button variant="outline" className="px-2.5 py-1.5 text-xs">
                  Route 360
                </Button>
              </Link>
            )
          }
        />
      ))}
    </div>
  );
}

export function RouteEmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-dashed border-primary/15 bg-gray-bg/40">
      <EmptyState title={title} hint={hint} />
    </div>
  );
}

export function RouteErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
      {message}
    </div>
  );
}

export function RoutePageIntro({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <h2 className="text-lg font-bold text-primary">{title}</h2>
        {description && <p className="mt-1 max-w-2xl text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Route360Header({
  plan,
  breadcrumb,
  actions,
}: {
  plan: RoutePlan;
  breadcrumb?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-5 shadow-sm">
      {breadcrumb}
      <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary/10 text-secondary">
              <Route className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-xl font-bold text-primary">{plan.name}</h2>
              <div className="mt-1 flex flex-wrap gap-2">
                <RouteStatusBadge status={plan.status} />
                <Badge tone="slate">{titleCase(plan.strategy)}</Badge>
                {plan.requires_approval ? <Badge tone="amber">Approval required</Badge> : null}
              </div>
            </div>
          </div>
          <p className="mt-3 text-xs text-muted">
            {plan.order_ids.length} orders · {plan.stops.length} stops
            {plan.driver_id ? " · Driver assigned" : " · No driver assigned"}
          </p>
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
    </div>
  );
}

export function RouteStopTimeline({ stops }: { stops: RoutePlan["stops"] }) {
  if (stops.length === 0) {
    return (
      <RouteEmptyState
        title="No stops on this route"
        hint="Add orders in Route Builder to generate stops."
      />
    );
  }

  return (
    <ol className="space-y-0">
      {stops.map((stop, i) => (
        <li
          key={`${stop.order_id}-${stop.type}-${i}`}
          className="relative flex gap-4 pb-6 last:pb-0"
        >
          {i < stops.length - 1 && (
            <span
              className="absolute left-[15px] top-8 h-[calc(100%-1rem)] w-0.5 bg-primary/10"
              aria-hidden
            />
          )}
          <span className="relative z-[1] flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-bold text-white">
            {i + 1}
          </span>
          <div className="min-w-0 flex-1 rounded-xl border border-primary/10 bg-gray-bg/30 px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium text-primary">{titleCase(stop.type)}</p>
              <Badge tone={stop.priority === "high" ? "red" : "slate"}>
                {stop.status ?? "pending"}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-muted">{stop.address ?? stop.tracking_number ?? "—"}</p>
            {stop.tracking_number && stop.address ? (
              <p className="mt-0.5 text-xs text-muted">{stop.tracking_number}</p>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
