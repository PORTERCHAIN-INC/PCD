const { getDefaultConfig } = require("expo/metro-config");
const fs = require("fs");
const path = require("path");

const projectRoot = __dirname;
const monorepoRoot = path.resolve(projectRoot, "../..");
const inMonorepo = fs.existsSync(path.join(monorepoRoot, "pnpm-workspace.yaml"));
const vendoredTheme = path.join(projectRoot, "vendor/mobile-theme");
const workspaceTheme = path.join(monorepoRoot, "packages/mobile-theme");
const themeRoot = fs.existsSync(path.join(vendoredTheme, "package.json"))
  ? vendoredTheme
  : workspaceTheme;

/** @type {import('expo/metro-config').MetroConfig} */
const config = getDefaultConfig(projectRoot);

if (inMonorepo) {
  config.watchFolders = [monorepoRoot, themeRoot];
  config.resolver.nodeModulesPaths = [
    path.resolve(projectRoot, "node_modules"),
    path.resolve(monorepoRoot, "node_modules"),
  ];
} else {
  config.watchFolders = [themeRoot];
}

config.resolver.extraNodeModules = {
  ...(config.resolver.extraNodeModules ?? {}),
  "@porterchain/mobile-theme": themeRoot,
};

module.exports = config;
