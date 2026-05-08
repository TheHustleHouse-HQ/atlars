# ATLARS Open Source Launch Checklist

Work through these in order. Don't skip steps.

---

## Stage 1 — Before Creating the Repo

- [x] GitHub organization created: [TheHustleHouse-HQ](https://github.com/TheHustleHouse-HQ)
- [x] Repo name decided: `atlars`
- [ ] Register `atlars.dev` or `atla.rs` domain (brand protection)
- [ ] Create a simple holding page or redirect to GitHub

---

## Stage 2 — Repo Setup (Day 1)

- [x] Repo created as **Public**
- [x] All documentation files in repo root
- [x] All placeholders replaced (company name, handles, emails)

**Branch protection — do this immediately:**
- [ ] Go to Settings → Branches → Add rule for `main`
- [ ] Check: "Require a pull request before merging"
- [ ] Check: "Require approvals" → set to 1
- [ ] Check: "Require status checks to pass before merging"
- [ ] Check: "Do not allow bypassing the above settings"
- [ ] Create `develop` branch — this is where contributors merge to

**Repository settings:**
- [ ] Settings → General → Features: enable Issues, Discussions, Projects
- [ ] Settings → General → turn OFF Wikis (use /docs folder instead)
- [ ] Add repository description: "Personal identity intelligence system. Longitudinal self-knowledge through data."
- [ ] Add topics: `personal-ai`, `identity-analytics`, `knowledge-graph`, `open-source`, `self-hosted`, `llm`, `python`, `fastapi`, `mongodb`

---

## Stage 3 — Content Before Launch

Before going public, create real content so the repo doesn't look empty.

- [ ] `docker-compose.dev.yml` — local MongoDB, Redis, backend, frontend, Celery worker
- [ ] `docker-compose.yml` — production skeleton with Atlas connection string
- [ ] `.env.example` — all required env vars with descriptions
- [ ] `backend/main.py` — FastAPI skeleton with `GET /health` route
- [ ] `backend/app/core/database.py` — MongoDB Motor connection
- [ ] `scripts/seed_dev.py` — seeds a test user and sample entries
- [ ] `backend/requirements.txt` — core dependencies listed

**Create 15+ issues before launch:**
- [ ] 5 labeled `good first issue` — small, self-contained, well-documented (see Phase 0 in `docs/ROADMAP.md`)
- [ ] 5 labeled `help wanted` — medium complexity
- [ ] 5 labeled `enhancement` — larger features from the roadmap
- [ ] Create a GitHub Project Board and add all issues to it

---

## Stage 4 — GitHub Settings

- [ ] Settings → Collaborators: do not add anyone yet
- [ ] Settings → Actions → Allow all actions (CI needs this)
- [ ] Settings → Secrets → Add `OPENROUTER_API_KEY_TEST` for CI
- [ ] Settings → Pages: leave off for now
- [ ] Enable GitHub Discussions: Settings → Features → Discussions ✅

**GitHub Project Board setup:**
- [ ] Create a Project called "ATLARS Roadmap"
- [ ] Columns: `Backlog` / `Phase 0` / `Phase 1` / `Phase 2` / `In Progress` / `Review` / `Done`
- [ ] Add all issues to the board with correct phase

---

## Stage 5 — App Store Accounts Setup

Do this early — Apple approval can take 1–2 weeks for new accounts.

- [ ] Create Apple Developer account at developer.apple.com ($99/year)
- [ ] Create App Store Connect app entry — bundle ID: `com.thehustlehouse.atlars`
- [ ] Create Google Play Console account at play.google.com/console ($25 one-time)
- [ ] Create Play Store app entry — package name: `com.thehustlehouse.atlars`
- [ ] Install EAS CLI: `npm install -g eas-cli`
- [ ] Log in to EAS: `eas login`
- [ ] Run `eas build:configure` in the `mobile/` directory — generates `eas.json`
- [ ] Configure Apple signing: `eas credentials` (EAS manages provisioning profiles)
- [ ] Set `OPENROUTER_API_KEY` and `MONGO_ATLAS_URI` as EAS secrets (never in code)
- [ ] Set production API base URL in `eas.json` production build profile env vars
- [ ] Write App Store description, keywords, and privacy policy URL (required before submission)
- [ ] Create app screenshots for required iPhone sizes (6.7" and 6.1" minimum)
- [ ] Create Play Store screenshots (phone + 7" tablet minimum)
- [ ] Complete Apple App Privacy section in App Store Connect (data types, purposes)
- [ ] Complete Google Play Data Safety form

---

## Stage 6 — Credly Setup (for contributor certificates)

- [ ] Create account at credly.com
- [ ] Set up The Hustle House organization on Credly
- [ ] Design two badge templates:
  - "ATLARS 5-Contribution Badge" (for 5+ contributions)
  - "ATLARS Contributor Certificate" (for 10+ contributions)
- [ ] Include in each badge: skills demonstrated, what ATLARS is, The Hustle House name
- [ ] Test issuing one badge to yourself before launch

---

## Stage 7 — Launch

**On launch day:**
- [ ] Post on LinkedIn — explain the project and the contributor program
- [ ] Post on X/Twitter
- [ ] Post on Reddit: r/opensource, r/selfhosted, r/MachineLearning, r/Python
- [ ] Post on dev.to (short article about ATLARS, link to repo)
- [ ] Submit to goodfirstissue.dev — auto-indexes repos with `good first issue` labels
- [ ] Submit to Product Hunt (optional but high visibility)

---

## Stage 8 — Ongoing Maintenance

**Weekly:**
- [ ] Review open PRs (respond within 72 hours)
- [ ] Triage new issues (label, assign priority)
- [ ] Check for claimed issues gone silent (>7 days without update)

**Monthly:**
- [ ] Review contribution counts — who hit 5+, who hit 10+?
- [ ] Issue Credly badges to qualified contributors
- [ ] Select internship candidates from top contributors
- [ ] Post a monthly update in GitHub Discussions: what shipped, what's next
- [ ] Update the Project Board

---

## What Must Never Go in the Repo

- [ ] API keys (use `.env` only, never commit)
- [ ] User data, even anonymized test data
- [ ] Passwords, database credentials, connection strings

---

*Once Stage 1–4 items are checked, the repo is ready to go public. Stage 5 (app store accounts) must be complete before Phase 5 of the build begins.*
