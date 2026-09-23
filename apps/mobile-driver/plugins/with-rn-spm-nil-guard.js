/**
 * React Native 0.86 CocoaPods SPM hook crashes EAS "Install pods":
 *   undefined method `package_product_dependencies' for nil
 *
 * ClerkExpo declares clerk-ios as an SPM product. On EAS / CocoaPods 1.15+
 * that target can live in a pod subproject, so
 * installer.pods_project.targets.find returns nil.
 */
const { withDangerousMod } = require("expo/config-plugins");
const fs = require("fs");
const path = require("path");

const MARKER = "Porterchain SPM nil-target guard";

const PATCH = [
  "    log 'Adding SPM dependencies to Pods project'",
  "    @dependencies_by_pod.each do |pod_name, dependencies|",
  "      target = nil",
  "      target_project = project",
  "      if project",
  "        target = project.targets.find { |t| t.name == pod_name }",
  "      end",
  "      if target.nil? && installer.respond_to?(:pod_target_subprojects)",
  "        installer.pod_target_subprojects.each do |sub|",
  "          found = sub.targets.find { |t| t.name == pod_name }",
  "          if found",
  "            target = found",
  "            target_project = sub",
  "            break",
  "          end",
  "        end",
  "      end",
  "      unless target",
  '        log "Skipping SPM for #{pod_name}: no matching Xcode target"',
  "        next",
  "      end",
  "      dependencies.each do |spm_spec|",
  '        log "Adding SPM dependency on product #{spm_spec[:products]}"',
  "        add_spm_to_target(",
  "          target_project,",
  "          target,",
  "          spm_spec[:url],",
  "          spm_spec[:requirement],",
  "          spm_spec[:products]",
  "        )",
  '        log " Adding workaround for Swift package not found issue"',
  "        target.build_configurations.each do |config|",
  "          target.build_settings(config.name)['SWIFT_INCLUDE_PATHS'] ||= ['$(inherited)']",
  "          search_path = '${SYMROOT}/${CONFIGURATION}${EFFECTIVE_PLATFORM_NAME}/'",
  "          unless target.build_settings(config.name)['SWIFT_INCLUDE_PATHS'].include?(search_path)",
  "            target.build_settings(config.name)['SWIFT_INCLUDE_PATHS'].push(search_path)",
  "          end",
  "        end",
  "      end",
  "    end",
  "",
].join("\n");

function patchSpmRb(spmPath) {
  let src = fs.readFileSync(spmPath, "utf8");
  if (src.includes(MARKER)) {
    return false;
  }
  src = src.replace(
    "def add_spm_to_target(project, target, url, requirement, products)\n",
    "def add_spm_to_target(project, target, url, requirement, products)\n    return unless target\n"
  );
  const start = src.indexOf("    log 'Adding SPM dependencies to Pods project'");
  const end = src.indexOf("    unless @dependencies_by_pod.empty?");
  if (start < 0 || end < 0 || end <= start) {
    throw new Error("Could not locate SPM apply loop in " + spmPath);
  }
  src = src.slice(0, start) + "    # " + MARKER + "\n" + PATCH + src.slice(end);
  fs.writeFileSync(spmPath, src);
  return true;
}

function withRnSpmNilGuard(config) {
  return withDangerousMod(config, [
    "ios",
    async (modConfig) => {
      const root = modConfig.modRequest.projectRoot;
      const rnRoot = path.dirname(require.resolve("react-native/package.json", { paths: [root] }));
      const spmPath = path.join(rnRoot, "scripts/cocoapods/spm.rb");
      if (!fs.existsSync(spmPath)) {
        throw new Error("react-native spm.rb missing at " + spmPath);
      }
      const changed = patchSpmRb(spmPath);
      console.log(
        changed
          ? "✅ Patched React Native SPM CocoaPods hook (" + MARKER + ")"
          : "✅ React Native SPM CocoaPods hook already patched"
      );
      return modConfig;
    },
  ]);
}

module.exports = withRnSpmNilGuard;
module.exports.patchSpmRb = patchSpmRb;
