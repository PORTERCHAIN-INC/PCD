const { getDefaultConfig } = require("expo/metro-config");
const path = require("path");

const projectRoot = __dirname;
const monorepoRoot = path.resolve(projectRoot, "../..");

const config = getDefaultConfig(projectRoot);

config.watchFolders = [monorepoRoot];

// Only resolve from app + root node_modules (skip nested copies in shared/*).
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, "node_modules"),
  path.resolve(monorepoRoot, "node_modules"),
];
config.resolver.disableHierarchicalLookup = true;

// Pin singletons — shared/* packages may install react@19 for web peers.
const singletons = ["react", "react-native", "react-dom"];
config.resolver.extraNodeModules = Object.fromEntries(
  singletons.map((name) => [name, path.resolve(monorepoRoot, "node_modules", name)])
);

module.exports = config;
