#!/usr/bin/env bash
# Archive Porterchain Customer (PCDC) with Xcode and export an App Store IPA.
# Expo SDK stays for RN modules; this only replaces EAS Build / EAS Submit.
#
# Usage:
#   cd apps/mobile-customer
#   bash scripts/archive-ios-testflight.sh
#
# Requires Xcode 27 so DTSDKName is iphoneos27.0.
# ASC app 6787763001 · bundle com.porterchain.customer · SKU 202222 · team 4XWFT5A8C3
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IOS="$ROOT/ios"
WORKSPACE="$IOS/PorterchainCustomer.xcworkspace"
SCHEME="PorterchainCustomer"
ARCHIVE_PATH="${ARCHIVE_PATH:-$ROOT/build/PorterchainCustomer.xcarchive}"
EXPORT_DIR="${EXPORT_DIR:-$ROOT/build/export}"
EXPORT_PLIST="$ROOT/build/ExportOptions-appstore.plist"

cd "$ROOT"

if [[ ! -d "$WORKSPACE" ]]; then
  echo "Missing $WORKSPACE — run: pnpm prebuild && cd ios && pod install"
  exit 1
fi

export EXPO_PUBLIC_APP_ENV=production
export EXPO_PUBLIC_ALLOW_DEV_AUTH=false
export EXPO_PUBLIC_API_URL="${EXPO_PUBLIC_API_URL:-https://api.porterchain.com}"
export EXPO_USE_PRECOMPILED_MODULES=0
# Do not bake apps/mobile-customer/.env (test Platform key) into the Release bundle.
export EXPO_NO_DOTENV=1

# Live PorterChain Platform key. Do not use the driver instance or the local test .env.
KEYS="$ROOT/../../infrastructure/deploy/scripts/clerk-keys.local.env"
if [[ -f "$KEYS" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$KEYS"
  set +a
  if [[ -n "${CLERK_CUSTOMER_PUBLISHABLE_KEY:-}" ]]; then
    export EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY="$CLERK_CUSTOMER_PUBLISHABLE_KEY"
  elif [[ -n "${CLERK_PUBLISHABLE_KEY:-}" ]]; then
    export EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY="$CLERK_PUBLISHABLE_KEY"
  fi
fi

if [[ -z "${EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY:-}" ]]; then
  echo "Set EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY to the live PorterChain Platform key (clerk.admin.porterchain.com) before archiving."
  exit 1
fi

# Places autocomplete only. Same public browser key the customer website uses.
if [[ -z "${EXPO_PUBLIC_GOOGLE_MAPS_API_KEY:-}" && -f "$ROOT/../../env/.env" ]]; then
  EXPO_PUBLIC_GOOGLE_MAPS_API_KEY="$(python3 - "$ROOT/../../env/.env" <<'PY'
import sys
key = ""
for line in open(sys.argv[1]):
    if line.startswith("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY="):
        key = line.split("=", 1)[1].strip().strip('"')
        break
print(key, end="")
PY
)"
  export EXPO_PUBLIC_GOOGLE_MAPS_API_KEY
fi
if [[ -z "${EXPO_PUBLIC_GOOGLE_MAPS_API_KEY:-}" ]]; then
  echo "Set EXPO_PUBLIC_GOOGLE_MAPS_API_KEY so pickup and drop-off can search Google Places."
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
echo "Confirm Info.plist has UISceneDelegateClassName = EXExpoAppSceneDelegate and CFBundleVersion above 1."
echo "Upload with Transporter. ASC app: https://appstoreconnect.apple.com/apps/6787763001/testflight/ios"
