# 50 · Mobile release train and store checklists

**Train:** every 2 weeks from week 9. Branch `release/x.y` → Maestro smoke → EAS Build (free tier, or `eas build --local` on Ubuntu if the queue is slow) → TestFlight + Play internal → 3-day staff test → staged rollout 10% → 100%. JS-only fixes go out with EAS Update to the matching runtime version; native changes need a store build. Versions: semver, with `runtimeVersion` policy `appVersion`. Crashes are reported to GlitchTip.

## Apple App Store checklist (week 11)

- Account deletion inside the app (exists: `accountDeletion.ts`).
- Background location purpose strings (driver app). Justify continuous location for the delivery job and show a visible indicator.
- **Sign in with Apple is mandatory** (guideline 4.8): Google sign-in is offered (L36, 74 §3).
- Privacy nutrition labels updated after removing Clerk/Sentry/Google.
- Fix the customer app associated domains (doc 25).
- Demo account for review; no placeholder content; push permission prompt with a reason.
- Medical cooler wording: no health claims.

## Google Play checklist (week 11, if Android ships: mandatory fee)

- Data safety form; background location declaration + video; target API level current; account deletion URL; content rating.
