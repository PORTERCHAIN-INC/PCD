import { solutionVerticalPath } from "@/lib/solutions-verticals";

/** Tab destinations formerly in the Solutions navbar dropdown. */

export type SolutionsTabId =
  | "overview"
  | "wholesale"
  | "medical"
  | "foodBeverage"
  | "construction"
  | "industries"
  | "serviceAreas";

export type SolutionsTabItem = {
  id: SolutionsTabId;
  href: string;
};

export const SOLUTIONS_TAB_ITEMS: readonly SolutionsTabItem[] = [
  { id: "overview", href: "/solutions" },
  { id: "wholesale", href: solutionVerticalPath("wholesale") },
  { id: "medical", href: solutionVerticalPath("medical") },
  { id: "foodBeverage", href: solutionVerticalPath("food-beverage") },
  { id: "construction", href: solutionVerticalPath("construction") },
  { id: "industries", href: "/business#industries" },
  { id: "serviceAreas", href: "/service-areas" },
] as const;

export function isSolutionsTabActive(pathname: string, item: SolutionsTabItem): boolean {
  if (item.id === "overview") {
    return pathname === "/solutions";
  }
  if (item.id === "industries") {
    return pathname === "/business" || pathname.startsWith("/industry/");
  }
  if (item.id === "serviceAreas") {
    return pathname === "/service-areas" || pathname.startsWith("/service-areas/");
  }
  if (item.id === "construction") {
    return pathname === "/construction" || pathname.startsWith("/construction/");
  }
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}
