# Contributing to ATLARS

Welcome. If you're reading this, you're considering putting real time into something that matters. ATLARS is not a toy project — it's a serious system built for a real problem. We want contributors who treat it that way.

This document covers everything: how to contribute, what qualifies, and how to go from your first PR to an internship.

---

## Before You Start

1. **Read the README** — understand what ATLARS is and what it isn't
2. **Read [`ARCHITECTURE.md`](ARCHITECTURE.md)** — understand the four pillars, the data model, and how the system fits together
3. **Read [`docs/ROADMAP.md`](docs/ROADMAP.md)** — understand which phase is active and what's open for contribution
4. **Read [`docs/FOLDER_STRUCTURE.md`](docs/FOLDER_STRUCTURE.md)** — understand where code goes before you write any
5. **Browse open issues** — especially those labeled `good first issue` or `help wanted`
6. **Do not open a PR without claiming the issue first** — comment on the issue, wait for acknowledgment

---

## Project State

ATLARS is at **Day 0** — the codebase scaffold is being built. No application code exists yet. The architecture, data model, API contract, and folder structure are fully designed and documented. Code is being written in phases as defined in [`docs/ROADMAP.md`](docs/ROADMAP.md).

If you're an early contributor (Phase 0), you are building the foundation everything else runs on. That's the highest-leverage place to contribute.

---

## Development Setup

### Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Node.js 20+
- Git
- For mobile contributors: Xcode (iOS) or Android Studio (Android), or a physical device with the Expo Go app

### Step 1 — Clone and Configure

```bash
git clone https://github.com/TheHustleHouse-HQ/atlars.git
cd atlars

# Copy environment template
cp .env.example .env
# Open .env and add your OpenRouter API key (free tier works for development)
# All other values have working defaults for local dev
```

### Step 2 — Start the Backend

```bash
# Starts: MongoDB, Redis, FastAPI backend, Celery worker, Celery Beat scheduler
docker compose -f docker-compose.dev.yml up

# In a second terminal, seed local data
python scripts/seed_dev.py
```

Backend API is live at `http://localhost:8000`  
Interactive API docs: `http://localhost:8000/docs`

No MongoDB Atlas account is required. The dev Docker Compose runs a local MongoDB instance.

### Step 3 — Run the Mobile App (frontend contributors only)

```bash
cd mobile
npm install
npx expo start
```

Options from the Expo CLI:
- Press `i` — iOS Simulator (requires Xcode on macOS)
- Press `a` — Android emulator (requires Android Studio)
- Scan QR code — open in Expo Go on your physical phone (fastest option, no emulator needed)

The app connects to `http://localhost:8000` by default. On a physical device, replace `localhost` with your machine's local IP (e.g. `http://192.168.1.x:8000`) in `mobile/src/lib/config.ts`.

### Running Backend Without Docker

```bash
cd backend

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
pip install -r requirements-dev.txt

# Start FastAPI dev server
uvicorn main:app --reload

# In a separate terminal, start Celery worker
celery -A app.workers.celery_app worker -Q daily,weekly,monthly --loglevel=info
```

Requires local MongoDB and Redis. Easiest: `docker compose -f docker-compose.dev.yml up mongo redis`

### Running Tests

```bash
cd backend
pytest                          # all tests
pytest tests/unit/              # unit tests only (no DB required)
pytest tests/integration/       # integration tests (requires running MongoDB)
```

---

## How to Contribute

### Step 1 — Find an Issue

Browse: `https://github.com/TheHustleHouse-HQ/atlars/issues`

| Label | Meaning |
|-------|---------|
| `good first issue` | Scoped, self-contained, great for new contributors |
| `help wanted` | We want external contributors on this |
| `bug` | Something broken |
| `enhancement` | New feature or improvement |
| `documentation` | Docs work |
| `needs-investigation` | Unclear root cause — good for experienced contributors |

### Step 2 — Claim It

Comment: *"I'd like to work on this."*

A maintainer will assign it to you. Do not submit a PR for an unclaimed issue.

You have **7 days** from claim to submit a draft PR. Comment on the issue if you need more time. Silence = issue becomes available again.

### Step 3 — Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/what-youre-fixing
# or
git checkout -b docs/what-youre-documenting
```

Branch naming:
- `feature/` — new functionality
- `fix/` — bug fixes
- `docs/` — documentation only
- `refactor/` — restructuring without behavior change
- `test/` — adding or improving tests

### Step 4 — Commit

```
feat: add voice entry transcription via whisperX
fix: resolve embedding job retry on OpenRouter timeout
docs: add maturity stage explanation to DATA_MODEL.md
test: add unit tests for contradiction detection pipeline
refactor: extract graph builder logic from entity extraction service
```

Format: `type: short description` — no capital, no period.

### Step 5 — Submit a PR

Use the PR template. Fill in every section:
- What this changes
- How you tested it
- Any trade-offs or open questions

**A PR with an empty description will be closed without review.**

### Step 6 — Engage in Review

- Address every review comment, even if just to explain why you disagree
- Don't just push fixes — respond to comments so we know you understand the feedback
- Quality of your engagement in review is part of how we evaluate contribution quality

---

## Code Standards

### Python (Backend)
- Python 3.11+
- Type hints on all functions and method signatures
- Docstrings on all public functions
- Black formatting: `black .`
- Linting: `flake8 .`
- Tests required for all new features — minimum one happy path, one edge case
- No OpenRouter calls in tests — mock the service layer

### TypeScript (Mobile)
- No `any` types
- ESLint: `npm run lint`
- Components in functional style with hooks
- No token management outside `mobile/src/lib/auth.ts` — access tokens stay in memory, refresh tokens use `expo-secure-store`. Never use `AsyncStorage` for tokens.

### General
- No secrets, API keys, or credentials in code — use `.env`
- No commented-out dead code in PRs
- If you change a public API, update `docs/API.md` in the same PR
- If you add a new collection or field, update `docs/DATA_MODEL.md` in the same PR

---

## Where to Put New Code

Before writing anything, read [`docs/FOLDER_STRUCTURE.md`](docs/FOLDER_STRUCTURE.md).

Quick reference:
- New API route → `backend/app/api/routes/`
- Request/response schema → `backend/app/models/`
- Business logic → `backend/app/services/` (organized by ATLARS pillar)
- Celery task → `backend/app/workers/` (correct schedule file)
- Frontend page → `frontend/src/app/`
- Reusable component → `frontend/src/components/` (in the correct pillar folder)

**Routes call services. Services call the database and OpenRouter. Never the other way.**

---

## What Counts as a Quality Contribution

Quality is the metric, not quantity.

**These count:**
- A bug fix that includes a regression test
- A new feature that solves an open issue, with tests
- Documentation that genuinely clarifies something confusing
- A PR review with substantive technical feedback (not just "LGTM")
- A well-reasoned Issue that leads to a significant fix or feature
- Performance improvement with before/after benchmarks

**These do not count:**
- Whitespace-only changes
- Trivial renaming with no functional impact
- Duplicate PRs
- Low-effort documentation
- PRs that break existing tests
- Copy-pasted code from elsewhere without attribution

---

## 🌟 The ATLARS Contributor Program

ATLARS is a real company building a real product. We built the contributor program because the best way to find exceptional people is to work with them.

### Milestones

| Milestone | Reward |
|-----------|--------|
| **First merged PR** | Added to Contributors section in README |
| **5+ quality contributions** | Digital credential badge (Credly) — shareable to LinkedIn |
| **10+ quality contributions** | ATLARS Contributor Certificate — issued by The Hustle House |
| **Top contributor of the month** | Internship consideration — 3 spots open per month |
| **Successful internship** | Full-time offer pathway |

### How Internship Selection Works

At the end of each month, we review the top contributors. We look at:
- Number and quality of merged PRs
- Engagement quality in reviews and issue discussions
- Whether they helped other contributors
- Communication clarity

Selected contributors receive a short async task (2–4 hours) and a conversation with the lead maintainer. That's the entire process.

---

## Issue Reporting

### Bugs
Use the Bug Report template. Include environment, reproduction steps, expected vs actual behavior, and error output.

### Feature Requests
Use the Feature Request template. Explain the problem, how your proposal fits the ATLARS architecture (which pillar?), and any alternatives considered.

### Security Issues
**Do not open a public issue.** See [`SECURITY.md`](SECURITY.md).

---

## Communication

- **GitHub Issues** — bugs, features, codebase questions
- **GitHub Discussions** — architecture ideas, showing what you built, broader conversations
- **PR comments** — code-specific feedback

We respond to all issues and PRs within **72 hours** on business days.

---

*— The Hustle House*
