/** Mutable admin profile for Vitest (delete gate, RBAC UI). */
export const adminProfileState: {
  role: string;
  email: string;
  permissions: string[];
} = {
  role: "super_admin",
  email: "sa@porterchain.com",
  permissions: ["system:all"],
};
