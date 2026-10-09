import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { afterEach, vi } from "vitest";
import { navigationState } from "./navigation-state";

afterEach(() => {
  cleanup();
});

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => navigationState.pathname,
  useSearchParams: () => new URLSearchParams(navigationState.search),
  useParams: () => ({}),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...rest
  }: {
    children: ReactNode;
    href: string;
  } & AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={typeof href === "string" ? href : "#"} {...rest}>
      {children}
    </a>
  ),
}));

// happy-dom 20 no longer defines the blocking dialogs; tests spy on them.
for (const name of ["confirm", "alert", "prompt"] as const) {
  if (typeof (window as unknown as Record<string, unknown>)[name] !== "function") {
    Object.defineProperty(window, name, {
      configurable: true,
      writable: true,
      value: name === "confirm" ? () => true : () => undefined,
    });
  }
}
