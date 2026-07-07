import { publicEnv } from "@/lib/env";

export type CareerDepartment =
  | "operations"
  | "engineering"
  | "sales"
  | "marketing"
  | "customerSuccess"
  | "driverSuccess"
  | "dispatch";

export interface CareerPosition {
  id: string;
  department: CareerDepartment;
}

export const careerDepartments: CareerDepartment[] = [
  "operations",
  "engineering",
  "sales",
  "marketing",
  "customerSuccess",
  "driverSuccess",
  "dispatch",
];

export const careerPositions: CareerPosition[] = [
  { id: "logistics-operations-manager", department: "operations" },
  { id: "senior-software-engineer", department: "engineering" },
  { id: "platform-engineer", department: "engineering" },
  { id: "account-executive", department: "sales" },
  { id: "growth-marketing-manager", department: "marketing" },
  { id: "customer-success-manager", department: "customerSuccess" },
  { id: "driver-partner-success-lead", department: "driverSuccess" },
  { id: "dispatch-coordinator", department: "dispatch" },
];

export const CAREERS_APPLY_EMAIL = publicEnv.contactEmail;
