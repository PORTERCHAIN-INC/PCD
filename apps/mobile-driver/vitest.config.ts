import { defineConfig } from "vitest/config";

// Unit tests for pure-TS driver logic (offline queue, errors, sign-out wipe). Native modules are mocked.
export default defineConfig({
  define: { __DEV__: "false" },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
