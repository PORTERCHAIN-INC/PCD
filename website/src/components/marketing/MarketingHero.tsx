/**
 * Canonical marketing hero primitive.
 * Prefer this import over the corporate path; implementation lives in HeroSection.
 *
 * Role-specific full-bleed heroes (business quote panel, vehicle partner apply)
 * are named exports — same kit, different composition, not MarketingHero props.
 */
export { default } from "@/components/marketing/corporate/sections/HeroSection";
export { default as BusinessQuoteHero } from "@/components/marketing/business/sections/BusinessHero";
export { default as VehiclePartnerHero } from "@/components/marketing/vehicle-partner/VehiclePartnerHero";
export { default as CareersHero } from "@/components/marketing/corporate/sections/CareersHero";
export { default as ContactHero } from "@/components/marketing/corporate/sections/ContactHero";
