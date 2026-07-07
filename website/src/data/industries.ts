import {
  Coffee,
  HeartPulse,
  Pill,
  UtensilsCrossed,
  Truck,
  Warehouse,
  HardHat,
  Zap,
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
}

export const industries: Industry[] = [
  { id: "coffee", icon: Coffee },
  { id: "medical", icon: HeartPulse },
  { id: "pharmacy", icon: Pill },
  { id: "restaurant", icon: UtensilsCrossed },
  { id: "food-distribution", icon: Truck },
  { id: "wholesale", icon: Warehouse },
  { id: "construction", icon: HardHat },
  { id: "electrical", icon: Zap },
  { id: "hvac", icon: Wind },
  { id: "auto-parts", icon: Car },
  { id: "retail", icon: ShoppingBag },
  { id: "ecommerce", icon: ShoppingCart },
  { id: "manufacturing", icon: Factory },
  { id: "laboratories", icon: FlaskConical },
  { id: "print-shops", icon: Printer },
];
