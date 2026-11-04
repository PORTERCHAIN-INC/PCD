import path from "node:path";
import { defineConfig } from "vitest/config";

// Unit tests for pure-TS driver logic (offline queue, errors, sign-out wipe). Native modules are mocked.
export default defineConfig({
  define: { __DEV__: "false" },
  resolve: {
    alias: {
      "@porterchain/driver-flows": path.resolve(__dirname, "vendor/driver-flows/src/index.ts"),
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
