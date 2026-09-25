"use client";

import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Box,
  Car,
  CarFront,
  Clock,
  Cloud,
  CreditCard,
  Eye,
  FileCheck,
  Globe,
  Handshake,
  Headphones,
  KeyRound,
  Layers,
  Leaf,
  Lock,
  Mail,
  Map,
  Package,
  Plug,
  Radio,
  RefreshCw,
  Scale,
  Server,
  Shield,
  ShieldCheck,
  Siren,
  Stamp,
  Target,
  Timer,
  Truck,
  Users,
} from "lucide-react";

/** Serializable icon keys for RSC → client FeatureSection props. */
export const FEATURE_ICONS = {
  shield: Shield,
  scale: Scale,
  leaf: Leaf,
  handshake: Handshake,
  lock: Lock,
  fileCheck: FileCheck,
  server: Server,
  stamp: Stamp,
  siren: Siren,
  keyRound: KeyRound,
  headphones: Headphones,
  target: Target,
  users: Users,
  shieldCheck: ShieldCheck,
  plug: Plug,
  layers: Layers,
  map: Map,
  radio: Radio,
  truck: Truck,
  timer: Timer,
  eye: Eye,
  barChart3: BarChart3,
  car: Car,
  carFront: CarFront,
  package: Package,
  box: Box,
  globe: Globe,
  refreshCw: RefreshCw,
  clock: Clock,
  cloud: Cloud,
  creditCard: CreditCard,
  mail: Mail,
} as const satisfies Record<string, LucideIcon>;

export type FeatureIconName = keyof typeof FEATURE_ICONS;

export function resolveFeatureIcon(name?: FeatureIconName): LucideIcon | undefined {
  return name ? FEATURE_ICONS[name] : undefined;
}
