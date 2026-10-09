export const BUSINESS_CHALLENGE_KEYS = [
  "driverUnavailable",
  "vehicleBreakdown",
  "urgentOrder",
  "fleetOverflow",
  "peakSeason",
  "forgottenMaterial",
  "jobsiteEmergency",
  "sameDayRequest",
] as const;

export const BUSINESS_SOLUTION_KEYS = [
  "recurringDelivery",
  "dedicatedRoutes",
  "sameDay",
  "multiStop",
  "wholesale",
  "ltlFreight",
  "urgentEmergency",
  "quickExpress",
  "construction",
  "medical",
  "fleetOverflow",
  "lastMile",
] as const;

export const BUSINESS_INDUSTRY_KEYS = [
  "coffee",
  "foodBeverage",
  "restaurantSuppliers",
  "grocery",
  "medical",
  "construction",
  "electrical",
  "hvac",
  "manufacturing",
  "automotive",
  "retail",
  "furniture",
  "laboratories",
  "ecommerce",
  "printShops",
  "industrial",
] as const;

export const BUSINESS_WHY_KEYS = [
  "realTimeTracking",
  "proofOfDelivery",
  "photoConfirmation",
  "digitalSignature",
  "flexibleBilling",
  "instantQuotes",
  "accountManager",
] as const;

export const BUSINESS_FLEET_KEYS = [
  "sedan",
  "suv",
  "pickup",
  "cargoVan",
  "highRoof",
  "box16",
  "box20",
] as const;

export const BUSINESS_BILLING_KEYS = ["payAsYouGo", "creditAccount", "enterprise"] as const;

export const BUSINESS_FAQ_KEYS = [
  "sameDay",
  "overflow",
  "jobsite",
  "lastMile",
  "intraCity",
  "gta",
  "vehicles",
  "pod",
  "pricing",
  "whatsIncluded",
  "overflowVsDedicated",
  "recurring",
  "multiStop",
  "contract",
  "monthly",
  "onboarding",
  "billing",
  "tracking",
  "insurance",
  "integrations",
  "api",
  "csv",
  "erp",
  "accountManager",
  "volume",
  "support",
  "custom",
  "security",
] as const;

export const BUSINESS_TRUSTED_KEYS = [
  "coffee",
  "medical",
  "manufacturing",
  "retail",
  "construction",
  "restaurant",
  "wholesale",
  "autoParts",
  "laboratories",
  "foodDistribution",
] as const;

import type { VehicleIllustrationType } from "@/components/marketing/illustrations/VehicleIllustration";
