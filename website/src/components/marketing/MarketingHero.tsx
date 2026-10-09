/**
 * Canonical marketing hero primitive.
 * Prefer this import over the corporate path; implementation lives in HeroSection.
 *
 * Role-specific full-bleed heroes (business quote panel, vehicle partner apply)
 * import their own modules directly (no barrel re-exports: they pull client JS into every page).
 */
export { default } from "@/components/marketing/corporate/sections/HeroSection";
