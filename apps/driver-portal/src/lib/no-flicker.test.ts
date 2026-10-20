import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const src = (rel: string) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8");

describe("driver portal anti-flicker guards", () => {
  it("does not wrap pages in a root view-transition cross-fade", () => {
    expect(src("../components/DriverShell.tsx")).not.toMatch(/RouteViewTransition/);
    expect(src("../app/globals.css")).not.toMatch(/::view-transition-(old|new)\(root\)/);
  });

  it("reserves a fixed-height slot for the Clerk sign-in card in every login state", () => {
    const page = src("../app/login/[[...sign-in]]/page.tsx");
    expect(page).toMatch(/const SIGN_IN_SLOT = "[^"]*min-h-\[/);
    // loading, signed-in "Preparing…", the <SignIn/> card, and the Suspense fallback
    expect(page.match(/className=\{SIGN_IN_SLOT\}/g)?.length).toBeGreaterThanOrEqual(4);
    expect(page).not.toMatch(/title="Loading"/);
  });

  it("only animates sidebar width after the saved collapsed state is restored", () => {
    const nav = src("../../../../packages/ui/src/app-nav.tsx");
    expect(nav).toMatch(/navReady && "transition-\[width\]"/);
    expect(nav).not.toMatch(/bg-white transition-\[width\] lg:flex/);
  });
});
