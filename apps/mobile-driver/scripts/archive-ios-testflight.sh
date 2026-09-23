#!/usr/bin/env bash
# Archive Porterchain Driver with Xcode and export an App Store IPA (no EAS).
# Expo SDK stays for RN modules; this only replaces EAS Build / EAS Submit.
#
# Usage:
#   cd apps/mobile-driver
#   bash scripts/archive-ios-testflight.sh
#
# Requires: Xcode, CocoaPods already installed, Apple Distribution cert +
# App Store provisioning for com.porterchain.PCD (Automatic signing OK if logged in).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IOS="$ROOT/ios"
WORKSPACE="$IOS/PorterchainDriver.xcworkspace"
SCHEME="PorterchainDriver"
ARCHIVE_PATH="${ARCHIVE_PATH:-$ROOT/build/PorterchainDriver.xcarchive}"
EXPORT_DIR="${EXPORT_DIR:-$ROOT/build/export}"
EXPORT_PLIST="$ROOT/build/ExportOptions-appstore.plist"

cd "$ROOT"

if [[ ! -d "$WORKSPACE" ]]; then
  echo "Missing $WORKSPACE — run: pnpm prebuild && cd ios && pod install"
  exit 1
fi

# Production public env (baked into JS at archive time via expo export:embed).
export EXPO_PUBLIC_APP_ENV=production
export EXPO_PUBLIC_ALLOW_DEV_AUTH=false
export EXPO_PUBLIC_API_URL="${EXPO_PUBLIC_API_URL:-https://api.porterchain.com}"
export EXPO_USE_PRECOMPILED_MODULES=0

# Prefer local Clerk live key file if present (not committed).
KEYS="$ROOT/../../infrastructure/deploy/scripts/clerk-keys.local.env"
if [[ -f "$KEYS" ]]; then
  # shellcheck disable=SC1090
  set -a
  # Only export driver publishable if defined in that file
  # shellcheck disable=SC1091
  source "$KEYS"
  set +a
  if [[ -n "${CLERK_DRIVER_PUBLISHABLE_KEY:-}" ]]; then
    export EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY="$CLERK_DRIVER_PUBLISHABLE_KEY"
  fi
fi

if [[ -z "${EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY:-}" ]]; then
  echo "Set EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY (pk_live…) before archiving."
  exit 1
fi

mkdir -p "$ROOT/build"
cat >"$EXPORT_PLIST" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>method</key>
  <string>app-store-connect</string>
  <key>destination</key>
  <string>export</string>
  <key>signingStyle</key>
  <string>automatic</string>
  <key>teamID</key>
  <string>4XWFT5A8C3</string>
  <key>uploadSymbols</key>
  <true/>
  <key>manageAppVersionAndBuildNumber</key>
  <false/>
</dict>
</plist>
PLIST

echo "==> Archiving $SCHEME (Release / generic iOS device)"
rm -rf "$ARCHIVE_PATH"
xcodebuild \
  -workspace "$WORKSPACE" \
  -scheme "$SCHEME" \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -archivePath "$ARCHIVE_PATH" \
  -allowProvisioningUpdates \
  DEVELOPMENT_TEAM=4XWFT5A8C3 \
  CODE_SIGN_STYLE=Automatic \
  archive

echo "==> Exporting App Store IPA → $EXPORT_DIR"
rm -rf "$EXPORT_DIR"
mkdir -p "$EXPORT_DIR"
xcodebuild \
  -exportArchive \
  -archivePath "$ARCHIVE_PATH" \
  -exportPath "$EXPORT_DIR" \
  -exportOptionsPlist "$EXPORT_PLIST" \
  -allowProvisioningUpdates

IPA="$(find "$EXPORT_DIR" -name '*.ipa' | head -1)"
if [[ -z "$IPA" ]]; then
  echo "No IPA produced under $EXPORT_DIR"
  exit 1
fi

echo ""
echo "IPA ready: $IPA"
echo "Upload to TestFlight (pick one):"
echo "  1) open -a Transporter && drop the IPA on Deliver"
echo "  2) xcrun altool --upload-app -f \"$IPA\" -t ios --apiKey <ASC_KEY_ID> --apiIssuer <ISSUER_ID>"
echo "ASC app: https://appstoreconnect.apple.com/apps/6781880626/testflight/ios"
