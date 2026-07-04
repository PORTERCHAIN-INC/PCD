import { adminFetch } from "@/lib/api";

export type AdminStaffProfile = {
  user_id: string;
  email: string;
  name: string | null;
  role: string;
  is_active: boolean;
};

export async function fetchAdminAccess(token: string): Promise<AdminStaffProfile> {
  return adminFetch<AdminStaffProfile>("/v1/auth/admin/access", token);
}
