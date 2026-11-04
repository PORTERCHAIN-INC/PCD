import type { LucideIcon } from "lucide-react";
import {
  Coffee,
  FlaskConical,
  HardHat,
  HeartPulse,
  Package,
  RefreshCw,
  ShoppingCart,
  Stethoscope,
  Truck,
  UtensilsCrossed,
  Warehouse,
  Wrench,
  Zap,
} from "lucide-react";

export type SolutionProgramConfig = {
  key: string;
  industrySlug: string;
  icon: LucideIcon;
};

export const SERVICE_AREA_REGIONS = [
  {
    key: "gta",
    slugs: ["toronto", "mississauga", "brampton", "vaughan", "markham", "ajax", "pickering"],
  },
  { key: "peelHalton", slugs: ["oakville", "burlington"] },
  { key: "durham", slugs: ["oshawa"] },
  {
    key: "southwest",
    slugs: ["kitchener-waterloo", "cambridge", "guelph", "hamilton", "london"],
  },
  { key: "niagara", slugs: ["st-catharines", "niagara"] },
] as const;
