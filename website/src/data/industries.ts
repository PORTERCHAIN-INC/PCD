import {
  HardHat,
  Zap,
  Wrench,
  Coffee,
  HeartPulse,
  Pill,
  UtensilsCrossed,
  Truck,
  Warehouse,
  Wind,
  Car,
  ShoppingBag,
  ShoppingCart,
  Factory,
  FlaskConical,
  Printer,
  type LucideIcon,
} from "lucide-react";

export interface Industry {
  id: string;
  icon: LucideIcon;
  featured?: boolean;
}

/** Construction trades first — primary marketing vertical. */
export const industries: Industry[] = [
  { id: "construction", icon: HardHat, featured: true },
  { id: "electrical", icon: Zap, featured: true },
  { id: "plumbing", icon: Wrench, featured: true },
  { id: "coffee", icon: Coffee },
  { id: "medical", icon: HeartPulse },
  { id: "pharmacy", icon: Pill },
  { id: "restaurant", icon: UtensilsCrossed },
  { id: "food-distribution", icon: Truck },
  { id: "wholesale", icon: Warehouse },
  { id: "hvac", icon: Wind },
  { id: "auto-parts", icon: Car },
  { id: "retail", icon: ShoppingBag },
  { id: "ecommerce", icon: ShoppingCart },
  { id: "manufacturing", icon: Factory },
  { id: "laboratories", icon: FlaskConical },
  { id: "print-shops", icon: Printer },
];
