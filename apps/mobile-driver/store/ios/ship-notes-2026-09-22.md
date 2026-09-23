# Mobile ship notes — 22 Sep 2026

Driver app tested, archived, and uploaded today. Customer app was not shipped. Use the customer section before repeating this path.

Ship path that worked: keep Expo modules, archive with Xcode, upload the IPA in Transporter. EAS cloud submit was slow and one submit was canceled.

## Driver app

| Item                  | Value                                                      |
| --------------------- | ---------------------------------------------------------- |
| App                   | Porterchain Driver                                         |
| Bundle                | `com.porterchain.PCD`                                      |
| ASC app               | `6781880626`                                               |
| Apple team            | `4XWFT5A8C3`                                               |
| Scheme in `app.json`  | `porterchain-driver`                                       |
| Clerk hosted callback | `com.porterchain.PCD://callback`                           |
| Clerk instance        | `ins_3G8jSfoAqasg906yFw0NNTPS9Tx`                          |
| Clerk host            | `clerk.driver.porterchain.com`                             |
| Stack                 | Expo SDK 57.0.24, React Native 0.86.3, `@clerk/expo` 4.6.6 |
| Local archive script  | `pnpm archive:ios` in `apps/mobile-driver`                 |
| IPA                   | `apps/mobile-driver/build/export/PorterchainDriver.ipa`    |

Production JS env for the archive: `EXPO_PUBLIC_API_URL=https://api.porterchain.com`, `EXPO_PUBLIC_APP_ENV=production`, `EXPO_PUBLIC_ALLOW_DEV_AUTH=false`. The publishable key comes from `CLERK_DRIVER_PUBLISHABLE_KEY` in `infrastructure/deploy/scripts/clerk-keys.local.env`. Local `apps/mobile-driver/.env` is the test Clerk key. A Release archive that picks up that file will talk to the wrong Clerk instance.

### Clerk settings that had to be on

- Native API enabled on the driver instance. While it was off, the app sat on “Starting Porterchain…” because Clerk `isLoaded` never became true (`native_api_disabled`).
- Redirect allowlist: Dashboard → Native applications → Allowlist for mobile SSO redirect. Clerk rejected `com.porterchain.PCD://callback` until that exact URL was allowlisted. No new binary was required for the allowlist alone.
- Associated domain on the app: `webcredentials:clerk.driver.porterchain.com`.
- `assetlinks.json` was `[]` and the Apple app site association was `{}` until the native app rows are saved in the Clerk dashboard. iOS row: team `4XWFT5A8C3`, bundle `com.porterchain.PCD`. Android row: package `com.porterchain.PCD` plus the SHA-256 cert fingerprints.

### What the phone actually showed

- Physical iPhone 15 Pro Max, not a simulator. A gray line said job-ring alerts need a physical device and that “this simulator cannot register FCM.” That copy was wrong. iOS was returning an APNs token. The API only accepts an FCM token that contains `:APA91`. Firebase Messaging is not wired, so job-ring push will keep failing until it is. `GoogleService-Info.plist` is present. `@react-native-firebase` is not.
- After Face ID, the red line was “Could not complete sign-in.” The API was rejecting the Clerk user. Codes to expect: `driver_user_not_provisioned`, `driver_not_found`, `user_not_provisioned`, `email_clerk_mismatch`, `clerk_email_required`, `clerk_email_unverified`, `invalid_driver_token`, `invalid_token`, `driver_suspended`, `driver_not_active`. The driver must be linked in Porterchain (`clerk_user_id` / email) before the app will leave sign-in. Sign out is the in-app way to switch accounts. A cached Clerk session will not return to the login screen by itself.
- Unsigned `/me` on launch used to paint that same red error before the user had signed in. The handshake now waits until the session is signed in.

### Crashes

1. Earlier TestFlight crash, before JS: ExpoCamera was built against an ExpoModulesCore that exports `BaseModule.willDestroy`, and the app resolved a different `expo-modules-core`. dyld aborted. EAS fix: `expo` 57.0.24, `ios.usePrecompiledModules: false`, `EXPO_USE_PRECOMPILED_MODULES=0`.
2. Today’s launch crash, build 1.0.0 (1), iOS 27 simulator, about two seconds after start: `UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption`. iOS 27 will not finish launching an app that still creates its window in `application(_:didFinishLaunchingWithOptions:)`. This was not the camera crash, and not Apple error 90725.
3. Apple error 90725 was an old 18 Jun 2026 upload built with the iOS 18.2 SDK. Current App Store uploads need the iOS 27 SDK (Xcode 27). Today’s archive reports `DTSDKName` `iphoneos27.0`.

### Builds uploaded or exported

| Build                                         | What happened                                                                                                                                                                                                                                                         |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EAS 13 `301c22ed-1142-4efb-bff6-46890c292cf1` | Submitted. Submission `4d022f1f-1485-4611-b6ff-b718e7d53736` finished.                                                                                                                                                                                                |
| EAS 14 `e23ac4a2-8cfc-46ef-b954-eb162ae1f26d` | Submission `72f15c21-e6f3-447a-bf1c-81023722fa1e` uploaded.                                                                                                                                                                                                           |
| EAS 15 `d311b159-5771-46f4-9271-c10f31233f02` | Built (sign-out fix). Submission `c9742584-47fd-43df-9141-e3bb7b646b2f` was canceled.                                                                                                                                                                                 |
| Xcode 1.0.0 (1)                               | Transporter delivery `7569040c-3edd-4b47-92a4-b90781c44238` went to processing. This is the scene-lifecycle crash. `app.json` `buildNumber` is still `"1"`. A pbxproj bump to 16 did not change that IPA because `Info.plist` had a literal `CFBundleVersion` of `1`. |
| Xcode 1.0.0 (16)                              | Exported 11:24. `CFBundleVersion` 16, SDK `iphoneos27.0`, `UISceneDelegateClassName` `EXExpoAppSceneDelegate` is in the binary. This is the IPA to upload. Install 16 from TestFlight, not build 1.                                                                   |

`eas.json` `appVersionSource` is `remote`, so EAS ignores `app.json` `buildNumber`. A local Xcode archive uses the `CFBundleVersion` string in `ios/PorterchainDriver/Info.plist`. After any accepted upload, raise that number before the next archive.

Signing: the Mac started with only an Apple Development cert. App Store export needs `-allowProvisioningUpdates` (the archive script already passes it). The EAS distribution cert stays on Expo’s servers. The local ASC API key is a different key from the EAS submit key.

### Scene lifecycle (required on this Xcode)

`expo-build-properties` → `ios.enableSceneSupport: true` (needs `expo` 57.0.23 or newer). That does three things:

- `AppDelegate` conforms to `ExpoReactNativeFactoryProvider` and only creates the React Native factory in `didFinishLaunching`.
- The window is created by Expo’s `EXExpoAppSceneDelegate`.
- `Info.plist` gets `UIApplicationSceneManifest` with `UISceneDelegateClassName` = `EXExpoAppSceneDelegate`.

Do not point the manifest at `$(PRODUCT_MODULE_NAME).SceneDelegate`. That is the SDK 58 form. SDK 57 does not generate a `SceneDelegate.swift`.

A long list of `.pcm` files while ClerkKit compiles is the Swift compiler input list, not a failure. Wait for `EXPORT SUCCEEDED` or `BUILD FAILED`.

### Do not rip Expo out

`@clerk/expo` needs the Expo modules (`expo-secure-store`, `expo-crypto`, `expo-auth-session`, `expo-web-browser`, `expo-constants`, `expo-local-authentication`, `expo-apple-authentication`). The app also uses camera, image picker, location, notifications, and linking through Expo. Xcode is only the archive and upload tool.

## Customer app — check before the same ship

`apps/mobile-customer` was not archived today. It will hit the same iOS 27 wall, and it is not on the driver Clerk setup.

| Item                          | Current value                                                                                                                          | Check                                                                                                                                                                                             |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bundle                        | `com.porterchain.customer`                                                                                                             | Register this exact id on the customer Clerk instance and in App Store Connect.                                                                                                                   |
| Scheme                        | `porterchain-customer`                                                                                                                 | Hosted Clerk callback will be `com.porterchain.customer://callback` if native auth matches the driver. Allowlist that URL.                                                                        |
| Expo                          | `~57.0.4`                                                                                                                              | Below 57.0.23. `enableSceneSupport` will refuse to run until Expo is at least 57.0.24 (same patch the driver is on).                                                                              |
| Scene lifecycle               | Not set. No `expo-build-properties`. No `ios/` project in the tree.                                                                    | After the Expo bump, set `ios.enableSceneSupport: true`, prebuild, and confirm `EXExpoAppSceneDelegate` is in the archived `Info.plist` before upload.                                            |
| Precompiled modules           | Not pinned off                                                                                                                         | Set `usePrecompiledModules: false` and `EXPO_USE_PRECOMPILED_MODULES=0`, or the ExpoCamera / `willDestroy` dyld crash can come back.                                                              |
| Clerk in the app              | No `@clerk/expo`. `eas.json` production env has API URL and `ALLOW_DEV_AUTH=false` only. No publishable key in the production profile. | Add the customer live key as `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` at archive time. Do not ship the test key from `apps/mobile-customer/.env`.                                                      |
| Associated domains            | `applinks:porterchain.com`, `applinks:www.porterchain.com` only                                                                        | Add `webcredentials:` for the customer Clerk host once that host exists. Save the iOS native app row (team `4XWFT5A8C3`, bundle `com.porterchain.customer`) or AASA stays empty.                  |
| `buildNumber` / `versionCode` | Both `1`                                                                                                                               | EAS `appVersionSource` is `remote`. A local archive will embed whatever literal is in `Info.plist` after prebuild. Confirm `CFBundleVersion` inside the IPA, not the Xcode project version alone. |
| Submit                        | `eas.json` submit production is empty                                                                                                  | No ASC app id recorded here. Create the App Store app before the first upload.                                                                                                                    |
| SDK                           | Not archived yet                                                                                                                       | Archive with Xcode 27 so `DTSDKName` is `iphoneos27.0`. An older SDK is rejected with 90725.                                                                                                      |
| Push                          | `GoogleService-Info.plist` is referenced. Notifications plugin is present.                                                             | Same FCM rule if the API expects an `:APA91` token. An APNs-only token will be rejected.                                                                                                          |
| Encryption                    | `ITSAppUsesNonExemptEncryption` false                                                                                                  | Same export compliance answer as the driver, if that is still true.                                                                                                                               |

Customer web portal Clerk is separate from this native app. Turning on Native API, the redirect allowlist, and the native app row are dashboard steps on the customer instance, not copies of the driver instance `ins_3G8jSfoAqasg906yFw0NNTPS9Tx`.

## Build 17 — 23 Sep 2026

Uploaded with altool key VMAB8YF54D. Delivery UUID `bd9c6461-fc0d-4dea-b3d6-365cac2ffb9a`. IPA `apps/mobile-driver/build/export/PorterchainDriver.ipa`. `CFBundleVersion` 17, SDK `iphoneos27.0`. This is the clover icon plus the whole-vehicle job screen. Install 17, not 16.

## Before the next TestFlight install

- Install build 17 once Apple finishes processing. Build 1 closes itself at launch on iOS 27.
- Sign in with a Clerk user that is already linked to an approved driver. Otherwise the app stays on the provisioned error and needs Sign out.
- Job-ring push on iOS will stay off until Firebase Messaging issues an FCM token.
