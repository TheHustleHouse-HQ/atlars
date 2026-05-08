# ATLARS Build Roadmap

> This document defines what gets built, in what order, and why.  
> Every open issue on the [Project Board](https://github.com/TheHustleHouse-HQ/atlars/projects) maps to a phase here.  
> Maintained by [The Hustle House](https://github.com/TheHustleHouse-HQ)

---

## How to Read This

Each phase has:
- **Goal** — what the system can do when this phase is complete
- **Deliverables** — the exact files and components being built
- **Contributor issues** — what's open for contributors during this phase

Phases are sequential. Phase 2 cannot start before Phase 1 is complete. Within a phase, individual deliverables can be worked on in parallel by different contributors.

Current status is tracked on the [GitHub Project Board](https://github.com/TheHustleHouse-HQ/atlars/projects).

---

## Phase 0 — Scaffold

**Status**: 🟡 In Progress  
**Goal**: Any contributor can clone the repo, run `docker compose up`, and have a fully working local environment with auth. No intelligence yet — just the skeleton that everything else is built on top of.

### Deliverables

**Infrastructure**
- `docker-compose.dev.yml` — spins up: local MongoDB, Redis, FastAPI backend, Next.js frontend
- `docker-compose.yml` — production config (Atlas connection string via env var)
- `.env.example` — every required environment variable documented with type and description
- `backend/Dockerfile` and `frontend/Dockerfile`
- `scripts/seed_dev.py` — seeds local MongoDB with a test user and sample entries for development

**Backend — Core**
- `backend/main.py` — FastAPI app entry point with CORS, lifespan events
- `backend/app/core/config.py` — all settings read from `.env` via Pydantic BaseSettings
- `backend/app/core/database.py` — Motor async MongoDB client, connection pool, typed collection accessors
- `backend/app/core/security.py` — JWT creation/decoding, bcrypt password hashing, refresh token logic

**Backend — Auth Routes**
- `POST /auth/register` — creates user, returns access token + sets refresh cookie
- `POST /auth/login` — validates credentials, returns access token + sets refresh cookie
- `POST /auth/refresh` — validates refresh cookie, issues new access token + rotates refresh token
- `POST /auth/logout` — clears refresh cookie server-side

**Backend — Models**
- `backend/app/models/user.py` — UserCreate, UserResponse, UserInDB Pydantic models
- `backend/app/api/deps.py` — `get_current_user` FastAPI dependency

**Mobile App**
- Expo (React Native) project with TypeScript, ESLint configured
- Login and Register screens connected to real auth API
- `src/lib/api.ts` — base API client with auth header injection and automatic token refresh on 401
- `src/lib/auth.ts` — secure token storage via `expo-secure-store` (never AsyncStorage)
- `src/lib/config.ts` — API base URL, switchable between dev (`localhost:8000`) and production

**Tests**
- Auth endpoint tests: register, login, refresh, logout, invalid credentials, duplicate email

### Contributor Issues Open in This Phase
- `[good first issue]` Add email format validation to `/auth/register`
- `[good first issue]` Add password minimum length validation (min 8 chars)
- `[good first issue]` Write unit tests for JWT expiry behavior
- `[help wanted]` Add rate limiting to `/auth/login` (max 5 attempts/minute per IP)
- `[help wanted]` Implement refresh token family invalidation on reuse detection

---

## Phase 1 — Capture

**Status**: ⚪ Not Started  
**Goal**: Users can submit text and voice entries. Every entry is stored in MongoDB and has an embedding vector generated asynchronously.

### Dependencies
- Phase 0 complete
- OpenRouter API key configured in `.env`

### Deliverables

**Celery Setup**
- `backend/app/workers/celery_app.py` — Celery app init, queue definitions (daily, weekly, monthly), Beat schedule
- Redis already running from Phase 0 docker-compose

**Text Entry**
- `POST /entries/` — accepts `{ raw_text, modality: "text", session_id? }`, stores in MongoDB, enqueues `embed_entry` task
- `GET /entries/` — paginated list of user's entries, newest first, with optional modality filter
- `GET /entries/{entry_id}` — single entry with all fields
- `PATCH /entries/{entry_id}` — edit raw_text (re-triggers embedding)
- `DELETE /entries/{entry_id}` — hard delete

**Voice Entry**
- `POST /entries/voice` — accepts audio file upload (mp3, wav, m4a, webm, max 25MB)
- whisperX pipeline: audio → word-level transcript with timestamps
- Transcript stored as `raw_text`, `audio_url` stored pointing to local file or object storage
- Same `embed_entry` Celery task runs after transcription

**Embedding Service**
- `backend/app/services/routing/openrouter.py` — OpenRouter async client, model routing table, retry logic
- `backend/app/services/synthesis/embedding.py` — generates 1536-dim nomic-embed-text embeddings
- `backend/app/workers/daily_jobs.py` — `embed_entry(entry_id)` Celery task

**Atlas Vector Search**
- `scripts/setup_atlas_index.py` — one-time script to create the `entries.embedding` knnVector index in Atlas
- Local dev: cosine similarity fallback in Python (no Atlas account required for contributors)

**Mobile App**
- Journal screen: text entry with character count, submit, success state
- Voice recorder component: uses `expo-av`, uploads audio blob to `/entries/voice`
- Entry list: shows recent entries with timestamp and modality badge

**Models**
- `backend/app/models/entry.py` — EntryCreate, EntryResponse, EntryInDB

**Tests**
- Entry CRUD tests
- Embedding task mock tests (should not make real OpenRouter calls in CI)
- Voice upload validation tests

### Contributor Issues Open in This Phase
- `[good first issue]` Add character count display to text entry frontend
- `[good first issue]` Add `modality` filter to `GET /entries/`
- `[good first issue]` Write entry CRUD unit tests
- `[help wanted]` Add micro-entry format (sub-50-word quick capture with separate UI affordance)
- `[help wanted]` Implement decision log entry type: `{ situation, options[], choice, reasoning }`
- `[enhancement]` Add entry search by semantic similarity (`POST /entries/search` with query string)
- `[enhancement]` Support entry tagging (user-defined free-form tags, stored as array on entry)

---

## Phase 2 — Synthesize

**Status**: ⚪ Not Started  
**Goal**: The system extracts structured intelligence from raw entries — traits, beliefs, contradictions, and the Life Graph — running daily as background jobs.

### Dependencies
- Phase 1 complete
- GLiNER2 model weights downloaded (see setup in `CONTRIBUTING.md`)
- Minimum 7 entries for a user (maturity_stage gate enforced before any synthesis)

### Deliverables

**Entity Extraction + Life Graph**
- `backend/app/services/graph/entity_extraction.py` — GLiNER2 pipeline: input raw text, output typed entities (Person, Place, Project, Event, Emotion, Belief, Goal) with confidence scores
- `backend/app/services/graph/graph_builder.py` — upserts `graph_nodes`, creates `graph_edges` with typed relationships and date
- Graph API:
  - `GET /graph/nodes` — list nodes for current user, filterable by type
  - `GET /graph/edges` — list edges, filterable by type and date range
  - `POST /graph/query` — natural language temporal query (e.g. "who was I working with in March?")

**Trait Extraction (Daily Job)**
- `backend/app/services/synthesis/trait_extraction.py` — batches recent entries, sends to Gemini Flash / Llama 3.1 8B via OpenRouter with structured output prompt, extracts OCEAN signal per entry, aggregates into `traits` collection
- `backend/app/workers/daily_jobs.py` — add `extract_traits(user_id)` task

**Belief Extraction (Daily Job)**
- `backend/app/services/synthesis/belief_extraction.py` — extracts value/belief statements from entries, stores in `beliefs` collection with domain classification and confidence
- `backend/app/workers/daily_jobs.py` — add `extract_beliefs(user_id)` task

**Contradiction Detection (Daily Job)**
- `backend/app/services/synthesis/contradiction_detection.py` — compares incoming beliefs against existing beliefs using NLI-style prompting, flags semantically inconsistent pairs in `contradictions` collection with severity score
- `backend/app/workers/daily_jobs.py` — add `detect_contradictions(user_id)` task

**API**
- `GET /traits/` — user's traits ordered by confidence
- `GET /beliefs/` — user's beliefs, filterable by domain and confirmed status
- `PATCH /beliefs/{id}` — user confirms, edits, or rejects a belief
- `GET /contradictions/` — flagged contradictions, filterable by severity and resolved status
- `PATCH /contradictions/{id}/resolve` — user marks a contradiction as understood/resolved

**Mobile App**
- Insights screen: OCEAN trait bars with confidence, labelled "Early estimate" until Day 30
- Beliefs list with confirm/reject per item
- Contradictions: paired belief cards with explanation and resolve button
- Life Graph screen: force-directed graph (react-native-svg), node type filter, date range slider

**Tests**
- Entity extraction unit tests with fixture text
- Contradiction detection unit tests with known contradictory/non-contradictory belief pairs
- Graph builder upsert logic tests

### Contributor Issues Open in This Phase
- `[good first issue]` Add belief confidence threshold filter to `GET /beliefs/`
- `[good first issue]` Write unit tests for contradiction detection scoring logic
- `[help wanted]` Add temporal date-range filter to `GET /graph/edges`
- `[help wanted]` Implement graph node merge (when two nodes refer to the same entity)
- `[enhancement]` Add contradiction resolution reasoning (user writes why it's not a contradiction)
- `[enhancement]` Add graph node search by label (`GET /graph/nodes?search=aryan`)

---

## Phase 3 — Reflect

**Status**: ⚪ Not Started  
**Goal**: Users can see who they are right now, compare to who they were, and receive focus recommendations generated from their own historical patterns — not generic advice.

### Dependencies
- Phase 2 complete
- Minimum 30 days of entries for domain scoring
- Celery Beat running weekly schedule

### Deliverables

**Life Domain Scoring (Weekly Job)**
- `backend/app/services/reflection/domain_scoring.py` — aggregates entries, traits, and graph edges per domain over the past 7 days, computes `activity_score` and `wellbeing_signal` (0–100 each) for all 8 domains
- `backend/app/workers/weekly_jobs.py` — `update_domain_scores(user_id)` task

**Identity Snapshots (Monthly Job)**
- `backend/app/services/reflection/snapshot_generator.py` — builds a versioned `snapshot` document capturing current state across all layers: OCEAN scores, domain scores, top beliefs, active life phase
- `backend/app/services/reflection/delta_compute.py` — diffs two snapshots to produce a structured delta (which traits shifted, which beliefs changed, which domains moved and by how much)
- `backend/app/workers/monthly_jobs.py` — `generate_snapshot(user_id)` task
- `GET /snapshots/` — list snapshots with date
- `GET /snapshots/{id}` — full snapshot
- `GET /snapshots/{id}/compare/{id2}` — returns delta between two snapshots

**Focus Recommendations**
- `backend/app/services/reflection/focus_recommendations.py` — generates 1–3 weekly focus recommendations from the user's own patterns (not external templates). Example: *"Your Creativity domain has dropped 40 points in 3 weeks. Your highest-output creative entries cluster on Tuesday mornings."*
- `GET /recommendations/` — current week's focus recommendations

**Mobile App**
- Dashboard screen: 8-domain radar chart + individual score cards with trend arrows
- Snapshots screen: chronological list + delta view between any two snapshots
- Focus recommendation cards (3 max, shown on dashboard)

**Tests**
- Domain scoring aggregation tests with fixture entry sets
- Delta compute tests with known before/after snapshot pairs

### Contributor Issues Open in This Phase
- `[good first issue]` Add domain score history chart (sparklines for each domain over time)
- `[good first issue]` Write unit tests for delta compute
- `[help wanted]` Implement snapshot JSON export (`GET /snapshots/{id}/export`)
- `[help wanted]` Add life stage inference to snapshot generator (activates at Day 90)
- `[enhancement]` Add domain score drill-down (which entries drove this week's Work score?)

---

## Phase 4 — Query & Compress

**Status**: ⚪ Not Started  
**Goal**: Users can ask natural language questions about themselves and manage their growing data through a transparent, user-controlled compression system.

### Dependencies
- Phase 3 complete

### Deliverables

**Natural Language Self-Query**
- `POST /query/` — accepts natural language question, retrieves relevant entries via `$vectorSearch`, constructs grounded context window, routes to Llama 3.1 70B via OpenRouter, returns answer with source entry references
- `GET /query/history` — past queries and responses
- `backend/app/services/routing/query_router.py` — context window construction, semantic retrieval, response grounding

**Context Compression**
- `backend/app/workers/monthly_jobs.py` — `generate_compression_candidates(user_id)` task: identifies entries eligible for Warm-tier archiving, generates candidate summary via Claude Haiku
- `GET /compression/candidates/` — pending compression candidates, each showing the proposed summary and the original entries it would replace
- `POST /compression/approve/{candidate_id}` — user approves: raw entries archived, summary stored as Warm-tier record
- `POST /compression/reject/{candidate_id}` — user rejects: entries remain Hot-tier, not re-proposed for 90 days
- `PATCH /entries/{entry_id}/permanent` — mark an entry as permanently exempt from compression

**Mobile App**
- Query screen: search-like interface with grounded responses, source attribution (which entries were used), query history
- Compression review UI: proposed summary + original entries listed — approve/reject controls

**Tests**
- Query context window construction tests (correct entries retrieved for known test questions)
- Compression candidate generation tests

### Contributor Issues Open in This Phase
- `[good first issue]` Add query history pagination
- `[help wanted]` Implement streaming responses for query API (SSE)
- `[help wanted]` Add source attribution highlighting (which parts of the answer came from which entry)
- `[enhancement]` Add compression rejection reason field (user explains why they rejected a summary)

---

## Phase 5 — Polish, Scale & App Store Release

**Status**: ⚪ Not Started  
**Goal**: ATLARS is production-ready, exports beautiful artifacts, passes a security audit, and ships to the App Store and Google Play.

### Deliverables

**Year-in-Review Export**
- `POST /exports/year-in-review` — triggers Claude Sonnet synthesis of the past 12 months into a narrative document covering identity evolution, key decisions, domain arcs, and contradictions resolved
- Returns structured Markdown, rendered as a shareable PDF in the mobile app

**Full Data Export**
- `GET /exports/full` — downloads the user's complete dataset as structured JSON: entries, traits, beliefs, decisions, snapshots, graph nodes, graph edges

**Self-Hosting Guide**
- `docs/SELF_HOSTING.md` — complete step-by-step for running the backend on a VPS with Docker Compose, Atlas setup, SSL via Caddy, and pointing the mobile app at your own server

**Mobile App Release**
- `eas.json` — EAS Build profiles: `development`, `preview` (TestFlight/internal track), `production`
- App Store Connect submission: app metadata, screenshots, privacy manifest, App Tracking Transparency
- Google Play Console submission: app bundle, store listing, content rating, data safety form
- OTA updates via EAS Update for JS-layer hotfixes (no re-submission needed for non-native changes)
- See `docs/MOBILE_RELEASE.md` for the full release checklist

**Hardening**
- Rate limiting on all routes
- Full integration test suite against a test database
- Performance profiling of synthesis jobs under multi-user load
- Security review of auth layer and namespace isolation

---

## What Will Never Be on the Roadmap

To be explicit about what ATLARS does not build:

- Social features, sharing, or public profiles
- AI that generates content in the user's voice
- Notifications designed to increase time-on-app
- Advertising or data selling
- Gamification (streaks, points, leaderboards)
