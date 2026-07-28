/** Tab destinations formerly in the Vehicles navbar dropdown. */

export type VehiclesTabId = "overview" | "cargoVan" | "tradeVan" | "boxTruck" | "pickupTruck";

export type VehiclesTabItem = {
  id: VehiclesTabId;
  href: string;
};

export const VEHICLES_TAB_ITEMS: readonly VehiclesTabItem[] = [
  { id: "overview", href: "/vehicles" },
  { id: "cargoVan", href: "/cargo-van-delivery" },
  { id: "tradeVan", href: "/trade-van-delivery" },
  { id: "boxTruck", href: "/box-truck-delivery" },
  { id: "pickupTruck", href: "/pickup-truck-delivery" },
] as const;

/** Paths that keep the top-level Vehicles nav item active. */
export const VEHICLES_NAV_PATHS = VEHICLES_TAB_ITEMS.map((item) => item.href);

export function isVehiclesTabActive(pathname: string, item: VehiclesTabItem): boolean {
  if (item.id === "overview") {
    return pathname === "/vehicles";
  }
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

export function isVehiclesNavActive(pathname: string): boolean {
  return VEHICLES_NAV_PATHS.some(
    (href) => pathname === href || (href !== "/vehicles" && pathname.startsWith(`${href}/`))
  );
}
