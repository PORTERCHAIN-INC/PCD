import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@porterchain/driver-flows": fileURLToPath(
        new URL("../../packages/driver-flows/src/index.ts", import.meta.url)
      ),
    },
  },
  test: { include: ["src/**/*.test.ts", "../../packages/driver-flows/src/**/*.test.ts"] },
});
