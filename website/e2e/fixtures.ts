import { test as base, expect } from "@playwright/test";

export type P0Case = {
  id: string;
  title: string;
  layer: string;
  runner: string;
  status: string;
};

export const test = base;
export { expect };

/** Mark a test with the SSOT case id for grep: `--grep @W-UI-002` */
export function tcId(id: string): string {
  return `@${id}`;
}

export function liveEnabled(): boolean {
  return process.env.WEBSITE_RUN_LIVE === "1";
}
