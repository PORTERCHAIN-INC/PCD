import { Building2, Shield, Truck, Users } from "lucide-react";
import type { UserDirectoryTab } from "@/lib/settings";

export const USER_TABS: Array<{
  id: UserDirectoryTab;
  label: string;
  icon: typeof Users;
  description: string;
}> = [
  { id: "staff", label: "Staff", icon: Shield, description: "Internal ops — admin portal access" },
  {
    id: "driver",
    label: "Drivers",
    icon: Truck,
    description: "Fleet drivers — driver portal & mobile",
  },
  {
    id: "merchant",
    label: "Merchants",
    icon: Building2,
    description: "B2B portal users by organization",
  },
  {
    id: "customer",
    label: "Customers",
    icon: Users,
    description: "Retail customers — website & customer portal",
  },
];

/** Columns shown per persona (post auth cutover). */
export type DirectoryColumn =
  "role" | "access" | "invitation" | "clerk" | "password" | "organization" | "added" | "actions";

export const DIRECTORY_COLUMNS: Record<UserDirectoryTab, DirectoryColumn[]> = {
  staff: ["role", "access", "added", "actions"],
  driver: ["role", "access", "invitation", "clerk", "password", "added", "actions"],
  merchant: ["role", "access", "organization", "added", "actions"],
  customer: ["role", "access", "added", "actions"],
};

export function tabMeta(tab: UserDirectoryTab) {
  return USER_TABS.find((t) => t.id === tab)!;
}
