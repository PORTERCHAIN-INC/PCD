import {
  Boxes,
  FlaskConical,
  HardHat,
  Pill,
  ShoppingBag,
  Sofa,
  Warehouse,
  Wrench,
  type LucideIcon,
} from "lucide-react";

/** Icon + hero photo (our own fleet photography) per /delivery vertical. */
export const VERTICAL_ICONS: Record<string, LucideIcon> = {
  "shopify-merchants": ShoppingBag,
  pharmacy: Pill,
  labs: FlaskConical,
  warehouses: Warehouse,
  "wholesale-traders": Boxes,
  construction: HardHat,
  "plumbing-electrical": Wrench,
  furniture: Sofa,
};

export type VerticalPhoto = { src: string; alt: string; width: number; height: number };

const van = { src: "/images/brand/vehicles/cargo-van.jpg", width: 1024, height: 581 };

export const VERTICAL_PHOTOS: Record<string, VerticalPhoto> = {
  "shopify-merchants": { ...van, alt: "PorterChain cargo van at a loading dock" },
  pharmacy: {
    src: "/images/brand/vehicles/sedan.jpg",
    alt: "PorterChain delivery sedan",
    width: 1024,
    height: 585,
  },
  labs: {
    src: "/images/brand/vehicles/suv.jpg",
    alt: "PorterChain delivery SUV",
    width: 1024,
    height: 585,
  },
  warehouses: {
    src: "/images/brand/warehouse-loading.jpg",
    alt: "PorterChain box truck being loaded at a warehouse",
    width: 2048,
    height: 1176,
  },
  "wholesale-traders": {
    src: "/images/brand/warehouse-dock.jpg",
    alt: "PorterChain box truck at a warehouse dock",
    width: 2048,
    height: 1176,
  },
  construction: {
    src: "/images/brand/urban-delivery.jpg",
    alt: "PorterChain box truck on a city delivery",
    width: 2048,
    height: 1176,
  },
  "plumbing-electrical": { ...van, alt: "PorterChain cargo van at a loading dock" },
  furniture: {
    src: "/images/brand/open-road.jpg",
    alt: "PorterChain box truck on the highway",
    width: 2560,
    height: 1454,
  },
};

export const VEHICLE_PHOTOS: Record<string, VerticalPhoto> = {
  sedan_suv: { src: "/images/brand/vehicles/sedan.jpg", alt: "", width: 1024, height: 585 },
  cargo_van: { src: "/images/brand/vehicles/cargo-van.jpg", alt: "", width: 1024, height: 581 },
  box_16: { src: "/images/brand/vehicles/box-truck.jpg", alt: "", width: 1024, height: 585 },
};
