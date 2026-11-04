import { defineConfig } from "@playwright/test";
/** Local-stack persona login/sign-out checks (LAN). Serial: Keycloak email codes are rate limited. */
export default defineConfig({
  testDir: ".",
  workers: 1,
  fullyParallel: false,
  timeout: 120_000,
  reporter: [["list"]],
  use: { screenshot: "only-on-failure", trace: "retain-on-failure" },
  outputDir: "/home/pcd/.pcd-local-stack/login-shots/spec-results",
});
