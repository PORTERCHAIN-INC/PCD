/**
 * Prebuilt React Native omits RCTPackagerConnection. The debug
 * expo-dev-launcher still attaches a category to that class, so
 * `expo run:ios` fails to link after lottie-ios is added.
 * Release does not link expo-dev-launcher.
 */
const { withDangerousMod } = require("expo/config-plugins");
const fs = require("fs");
const path = require("path");

const MARKER = "Porterchain: allow missing RCTPackagerConnection in debug";

const SNIPPET = `
    # ${MARKER}
    installer.aggregate_targets.each do |aggregate_target|
      aggregate_target.xcconfigs.each do |config_name, xcconfig|
        next unless config_name.to_s.downcase.include?('debug')
        flags = xcconfig.attributes['OTHER_LDFLAGS'] || '$(inherited)'
        token = '-Wl,-U,_OBJC_CLASS_$_RCTPackagerConnection'
        next if flags.include?(token)
        xcconfig.attributes['OTHER_LDFLAGS'] = "#{token} #{flags}"
        xcconfig.save_as(aggregate_target.xcconfig_path(config_name))
      end
    end
`;

function withPackagerConnectionLink(config) {
  return withDangerousMod(config, [
    "ios",
    (cfg) => {
      const podfile = path.join(cfg.modRequest.platformProjectRoot, "Podfile");
      const contents = fs.readFileSync(podfile, "utf8");
      if (contents.includes(MARKER)) return cfg;
      const next = contents.replace(
        /react_native_post_install\([\s\S]*?\)\n/,
        (match) => `${match}${SNIPPET}\n`
      );
      if (next === contents) {
        throw new Error("Could not find react_native_post_install in the Podfile");
      }
      fs.writeFileSync(podfile, next);
      return cfg;
    },
  ]);
}

module.exports = withPackagerConnectionLink;
