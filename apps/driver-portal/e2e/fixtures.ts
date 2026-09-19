/**
 * Shared Playwright fixtures for Driver portal P0 e2e.
 * Wire driver session via DRIVER_STORAGE_STATE (Playwright storageState JSON)
 * or DRIVER_RUN_LIVE=1 with local Clerk / email picker.
 *
 * Paths resolve from apps/driver-portal cwd (playwright config root).
 */
import fs from "fs";
import path from "path";
import { test as base, expect } from "@playwright/test";

export type P0Case = {
  id: string;
  title: string;
  persona: string;
  layer: string;
  runner: string;
  status: string;
  covers?: string[];
};

function loadRegistry(): { cases: P0Case[] } {
  const registryPath = path.join(process.cwd(), "../../docs/testing/driver_p0_registry.json");
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

/** Mark a test with the SSOT case id for grep: `--grep @UI-D-02` */
export function tcId(id: string): string {
  return `@${id}`;
}
