"use client";

import type { ComponentType, ReactNode } from "react";
import * as React from "react";

type ViewTransitionProps = {
  children?: ReactNode;
  default?: string;
};

/**
 * Soft route cross-fade when Next experimental.viewTransition is on.
 * Falls back to a plain fragment when ViewTransition is unavailable.
 */
export function RouteViewTransition({ children }: { children: ReactNode }) {
  const VT = (React as unknown as { ViewTransition?: ComponentType<ViewTransitionProps> })
    .ViewTransition;
  if (!VT) return <>{children}</>;
  return <VT default="auto">{children}</VT>;
}
