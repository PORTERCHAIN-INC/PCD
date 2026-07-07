import {
  Package,
  FileText,
  HeartPulse,
  Coffee,
  UtensilsCrossed,
  Warehouse,
  HardHat,
  Zap,
  Wrench,
  Sofa,
  Boxes,
  Truck,
  ShieldAlert,
  Thermometer,
  type LucideIcon,
} from "lucide-react";

export interface DeliveryType {
  id: string;
  icon: LucideIcon;
}

export const deliveryTypes: DeliveryType[] = [
  { id: "loose-parcel", icon: Package },
  { id: "documents", icon: FileText },
  { id: "medical", icon: HeartPulse },
  { id: "coffee", icon: Coffee },
  { id: "food-beverage", icon: UtensilsCrossed },
  { id: "wholesale", icon: Warehouse },
  { id: "construction", icon: HardHat },
  { id: "electrical", icon: Zap },
  { id: "plumbing", icon: Wrench },
  { id: "furniture", icon: Sofa },
  { id: "pallet-ltl", icon: Boxes },
  { id: "full-truck-ftl", icon: Truck },
  { id: "fragile", icon: ShieldAlert },
  { id: "temperature", icon: Thermometer },
];
