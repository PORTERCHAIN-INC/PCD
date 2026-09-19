/**
 * Shared Playwright fixtures for Website P0 e2e.
 * Paths resolve from website/ cwd (playwright config root).
 */
import fs from "fs";
import path from "path";
import { test as base, expect } from "@playwright/test";

export type P0Case = {
  id: string;
  title: string;
  layer: string;
  runner: string;
  status: string;
};

function loadRegistry(): { cases: P0Case[] } {
  const registryPath = path.join(process.cwd(), "../docs/testing/website_p0_registry.json");
  return JSON.parse(fs.readFileSync(registryPath, "utf8")) as { cases: P0Case[] };
}

const registry = loadRegistry();

export function playwrightCases(status?: "skeleton" | "implemented"): P0Case[] {
  return registry.cases.filter(
    (c) => c.runner === "playwright" && (status ? c.status === status : true)
  );
}

export const test = base;
export { expect };

/** Mark a test with the SSOT case id for grep: `--grep @W-UI-002` */
export function tcId(id: string): string {
  return `@${id}`;
}

export function liveEnabled(): boolean {
  return process.env.WEBSITE_RUN_LIVE === "1";
}
