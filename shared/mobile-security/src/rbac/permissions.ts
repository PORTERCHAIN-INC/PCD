import type { AuthPrincipal, Permission } from "../types";

export function hasPermission(principal: AuthPrincipal | null, permission: Permission) {
  if (!principal) return false;
  return principal.permissions.includes(permission) || principal.permissions.includes("system:all");
}

export function hasRole(principal: AuthPrincipal | null, role: string) {
  if (!principal) return false;
  return principal.roles.includes(role);
}

export function principalFromAuthMe(data: {
  user_id?: string;
  roles?: string[];
  permissions?: string[];
}): AuthPrincipal {
  return {
    userId: data.user_id ?? "",
    roles: data.roles ?? [],
    permissions: data.permissions ?? [],
  };
}
