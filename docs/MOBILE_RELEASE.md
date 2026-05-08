# ATLARS Mobile Release Process

> How the open-source codebase ships as a published app on the Apple App Store and Google Play Store.  
> Maintained by [The Hustle House](https://github.com/TheHustleHouse-HQ)

---

## Overview

Contributors build features on GitHub. The Hustle House owns the app store accounts and controls what ships to users. The pipeline looks like this:

```
GitHub (open source) → EAS Build (cloud build) → TestFlight / Internal Track (QA) → App Store / Play Store (public)
```

Contributors never need an Apple Developer account or Google Play Console access. Their job is to write correct, tested code. The Hustle House handles signing, submissions, and releases.

---

## Tools

| Tool | Purpose |
|------|---------|
| **Expo** | React Native framework — single codebase for iOS + Android |
| **EAS Build** | Cloud build service — compiles native binaries without needing a Mac |
| **EAS Update** | Over-the-air JS updates — hotfixes without a new store submission |
| **TestFlight** | Apple's beta distribution platform |
| **Google Play Internal Track** | Google's internal/beta distribution |

---

## Environments

Three build profiles are defined in `eas.json`:

| Profile | Backend | Distribution | Who uses it |
|---------|---------|--------------|-------------|
| `development` | `localhost:8000` | Expo Go / local device | Contributors during development |
| `preview` | Staging backend URL | TestFlight + Play Internal Track | QA, maintainers, trusted testers |
| `production` | Production backend URL | App Store + Play Store | Public users |

---

## Contributor Workflow (No App Store Access Needed)

Contributors work entirely in the `development` profile. The full local setup is in [CONTRIBUTING.md](../CONTRIBUTING.md).

```bash
cd mobile
npm install
npx expo start        # runs the dev build — points to localhost:8000
```

When a PR is merged to `main`, the CI pipeline automatically:
1. Runs backend tests (`pytest`)
2. Runs mobile lint (`npm run lint`)
3. Triggers an EAS `preview` build if tests pass

Contributors do not trigger builds manually.

---

## Release Pipeline (Maintainers Only)

### Step 1 — Feature Freeze

When a phase is complete and ready to ship:
- All PRs targeting the release are merged to `main`
- A release branch is cut: `release/v1.x.0`
- No new features merge to the release branch — only bug fixes

### Step 2 — Preview Build

```bash
eas build --platform all --profile preview
```

This produces:
- An `.ipa` file distributed to TestFlight (iOS)
- An `.aab` file uploaded to the Play Store internal track (Android)

QA runs against the preview build for 3–5 days.

### Step 3 — Production Build

```bash
eas build --platform all --profile production
```

### Step 4 — Submit to Stores

```bash
# iOS
eas submit --platform ios --latest

# Android
eas submit --platform android --latest
```

Apple review typically takes 1–3 days. Google Play review takes a few hours to 1 day.

### Step 5 — OTA Hotfixes (JS-only changes)

For bugs that only touch JavaScript (no native modules changed):

```bash
eas update --branch production --message "fix: description of fix"
```

Users receive the update automatically on next app launch. No re-submission to Apple or Google needed.

---

## What Requires a New Store Submission

| Change | Requires submission? |
|--------|---------------------|
| JS/TypeScript logic change | No — use EAS Update |
| New screen or component | No — use EAS Update |
| New native module (e.g. new Expo SDK package) | Yes |
| Change to `app.json` (name, bundle ID, permissions) | Yes |
| Any iOS Info.plist or Android Manifest change | Yes |

---

## App Store Assets (Maintained by The Hustle House)

These are not in the open-source repo:
- App icons and splash screens (final production versions)
- App Store screenshots and preview videos
- App Store Connect metadata (description, keywords, categories)
- Apple Developer certificates and provisioning profiles
- Google Play signing keystore

If you're contributing design work for these, coordinate via GitHub Discussions.

---

## Privacy Requirements

Both stores require explicit privacy declarations. ATLARS collects sensitive personal data (journal entries, beliefs, emotional states). The following must be declared and kept accurate:

**Apple App Store — Privacy Nutrition Label:**
- Data collected: Text content, audio recordings, usage data
- Data linked to identity: Yes
- Data used for tracking: No

**Google Play — Data Safety Form:**
- Personal info collected: Yes (name, email, journal content)
- Data shared with third parties: OpenRouter (LLM routing) — no raw journal data
- Data encrypted in transit: Yes
- User can request data deletion: Yes (via account deletion flow)

If you add a new data collection point, update `docs/PRIVACY_NOTES.md` and flag it in your PR description.

---

*The open-source nature of ATLARS means anyone can inspect exactly what data the app collects and what the backend does with it. That transparency is the foundation of user trust.*
