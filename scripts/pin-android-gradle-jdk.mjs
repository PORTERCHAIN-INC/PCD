#!/usr/bin/env node
/**
 * Expo prebuild writes gradle-daemon-jvm.properties with toolchainVersion=25
 * (Android Studio JBR). AGP Prefab treats JBR 25's
 * "restricted method in java.lang.System" stderr as a fatal CMake error.
 * Pin the Gradle daemon to JDK 17 after every prebuild.
 */
import { existsSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BODY = `# JDK 17 — Android Studio JBR 25 breaks AGP Prefab/CMake\ntoolchainVersion=17\n`;

for (const app of ["mobile-driver", "mobile-customer"]) {
  const dir = path.join(ROOT, "apps", app, "android", "gradle");
  if (!existsSync(dir)) continue;
  writeFileSync(path.join(dir, "gradle-daemon-jvm.properties"), BODY);
  console.log(`Pinned Gradle daemon JDK 17 for apps/${app}`);
}
