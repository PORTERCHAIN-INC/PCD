import type { VehicleIllustrationType } from "@/components/illustrations/VehicleIllustration";

export interface Vehicle {
  id: string;
  gradient: string;
  illustration: VehicleIllustrationType;
}

export const vehicles: Vehicle[] = [
  { id: "sedan", gradient: "from-[#1e3a5f] to-[#0f2744]", illustration: "sedan" },
  { id: "suv", gradient: "from-[#1e40af] to-[#1e3a5f]", illustration: "suv" },
  { id: "pickup", gradient: "from-[#1d4ed8] to-[#1e3a5f]", illustration: "pickup" },
  { id: "cargo-van", gradient: "from-[#2563eb] to-[#0f2744]", illustration: "cargo-van" },
  { id: "high-roof", gradient: "from-[#1e3a8a] to-[#0a1628]", illustration: "high-roof" },
  { id: "box-16", gradient: "from-[#1e3a5f] to-[#0a1628]", illustration: "box-16" },
  { id: "box-20", gradient: "from-[#0f2744] to-[#0a1628]", illustration: "box-20" },
];
