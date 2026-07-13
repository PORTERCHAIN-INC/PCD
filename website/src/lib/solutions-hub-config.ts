import type { LucideIcon } from "lucide-react";
import {
  Coffee,
  FlaskConical,
  HardHat,
  HeartPulse,
  ShoppingCart,
  Stethoscope,
  Truck,
  UtensilsCrossed,
  Wrench,
  Zap,
} from "lucide-react";
import type { SolutionVerticalSlug } from "@/lib/solutions-verticals";

export type SolutionProgramConfig = {
  key: string;
  industrySlug: string;
  icon: LucideIcon;
};

const ICONS = {
  warehouse: ShoppingCart,
  zap: Zap,
  wrench: Wrench,
  cart: ShoppingCart,
  heart: HeartPulse,
  flask: FlaskConical,
  stethoscope: Stethoscope,
  coffee: Coffee,
  utensils: UtensilsCrossed,
  truck: Truck,
  hardHat: HardHat,
} as const;

/** Message namespace key under corporate.solutions.* */
export const SOLUTION_MESSAGE_KEYS: Record<SolutionVerticalSlug, string> = {
  wholesale: "wholesale",
  medical: "medical",
  "food-beverage": "foodBeverage",
  construction: "construction",
};

export const SOLUTION_HUB_PROGRAMS: Record<SolutionVerticalSlug, SolutionProgramConfig[]> = {
  wholesale: [
    { key: "ecommerce", industrySlug: "ecommerce", icon: ICONS.cart },
    { key: "electrical", industrySlug: "electrical-distribution", icon: ICONS.zap },
    { key: "plumbing", industrySlug: "plumbing-supply", icon: ICONS.wrench },
  ],
  medical: [
    { key: "pharmacy", industrySlug: "pharmacy-medical", icon: ICONS.heart },
    { key: "lab", industrySlug: "lab-sample-delivery", icon: ICONS.flask },
    { key: "cosmetics", industrySlug: "cosmetics", icon: ICONS.stethoscope },
  ],
  "food-beverage": [
    { key: "coffee", industrySlug: "coffee-roasters", icon: ICONS.coffee },
    { key: "chocolate", industrySlug: "chocolate", icon: ICONS.utensils },
    { key: "wholesaleFood", industrySlug: "chocolate", icon: ICONS.truck },
  ],
  construction: [
    { key: "materials", industrySlug: "construction-materials", icon: ICONS.hardHat },
    { key: "electrical", industrySlug: "electrical-distribution", icon: ICONS.zap },
    { key: "plumbing", industrySlug: "plumbing-supply", icon: ICONS.wrench },
  ],
};

export const SOLUTION_HUB_CITY_SLUGS: Record<SolutionVerticalSlug, readonly string[]> = {
  wholesale: ["toronto", "mississauga", "brampton"],
  medical: ["toronto", "mississauga", "hamilton"],
  "food-beverage": ["toronto", "mississauga", "kitchener-waterloo"],
  construction: ["toronto", "mississauga", "brampton"],
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
