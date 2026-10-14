import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/** Drivers must never be shown links to staff/merchant/customer portals. */
function files(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    if (statSync(p).isDirectory()) return files(p);
    return /\.tsx?$/.test(n) && !/\.test\.tsx?$/.test(n) ? [p] : [];
  });
}

describe("driver portal chrome", () => {
  const src = files(join(__dirname, ".."));
  it("has no apps/portal switcher", () => {
    expect(src.filter((f) => /AppsMenu/.test(readFileSync(f, "utf8")))).toEqual([]);
  });
  it("never links to admin or merchant portals", () => {
    const bad =
      /NEXT_PUBLIC_(ADMIN_URL|MERCHANT_PORTAL_URL|CUSTOMER_PORTAL_URL)|admin\.porterchain\.com|merchant\.porterchain\.com/;
    expect(src.filter((f) => bad.test(readFileSync(f, "utf8")))).toEqual([]);
  });
});
