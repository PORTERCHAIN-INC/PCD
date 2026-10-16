import path from "node:path";
import { defineConfig } from "vitest/config";

// Unit tests for pure-TS customer app logic (display helpers, colour contrast).
export default defineConfig({
  define: { __DEV__: "false" },
  resolve: {
    alias: {
      "@porterchain/mobile-theme": path.resolve(__dirname, "vendor/mobile-theme/src/index.ts"),
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
