"use client";

import type { ReactNode } from "react";
import { hasPermission, hasRole } from "../rbac/permissions";
import { useMobileSecurity } from "../provider/MobileSecurityProvider";

export function PermissionGate({
  permission,
  role,
  fallback = null,
  children,
}: {
  permission?: string;
  role?: string;
  fallback?: ReactNode;
  children: ReactNode;
}) {
  const { principal } = useMobileSecurity();

  if (permission && !hasPermission(principal, permission)) return <>{fallback}</>;
  if (role && !hasRole(principal, role)) return <>{fallback}</>;
  return <>{children}</>;
}
