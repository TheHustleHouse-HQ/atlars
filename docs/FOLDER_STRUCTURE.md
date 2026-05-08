# ATLARS Folder Structure

> A guided walkthrough of the planned codebase layout.  
> This is the canonical reference for where to put new code.  
> For the build sequence, see [`docs/ROADMAP.md`](ROADMAP.md).

---

## Top-Level Layout

```
atlars/
├── backend/              # FastAPI Python backend
├── mobile/               # React Native (Expo) mobile app — iOS + Android
├── docs/                 # Extended documentation
├── scripts/              # One-time setup and utility scripts
├── .github/              # GitHub issue templates and PR template
├── docker-compose.yml        # Production Docker config (backend only)
├── docker-compose.dev.yml    # Local development Docker config (backend only)
└── .env.example              # All env vars documented
```

---

## Backend

```
backend/
├── main.py                          # FastAPI app entry point
├── requirements.txt                 # Production dependencies
├── requirements-dev.txt             # Dev/test dependencies (pytest, black, etc.)
├── Dockerfile                       # Production container
│
└── app/
    ├── api/
    │   ├── deps.py                  # FastAPI dependencies: get_current_user, get_db
    │   └── routes/
    │       ├── auth.py              # /auth/* — register, login, refresh, logout
    │       ├── entries.py           # /entries/* — CRUD, voice upload, search
    │       ├── graph.py             # /graph/* — nodes, edges, query
    │       ├── traits.py            # /traits/* — read only (system-generated)
    │       ├── beliefs.py           # /beliefs/* — read + user confirmation
    │       ├── contradictions.py    # /contradictions/* — read + resolve
    │       ├── snapshots.py         # /snapshots/* — list, get, compare
    │       ├── query.py             # /query/* — natural language self-query
    │       ├── compression.py       # /compression/* — candidates, approve, reject
    │       └── exports.py           # /exports/* — full export, year-in-review
    │
    ├── core/
    │   ├── config.py                # Settings from .env (Pydantic BaseSettings)
    │   ├── database.py              # Motor async MongoDB client + collection accessors
    │   └── security.py             # JWT creation/decoding, bcrypt hashing
    │
    ├── models/                      # Pydantic models for request validation + response shaping
    │   ├── user.py                  # UserCreate, UserResponse, UserInDB
    │   ├── entry.py                 # EntryCreate, EntryResponse, EntryInDB
    │   ├── trait.py                 # TraitResponse
    │   ├── belief.py                # BeliefResponse, BeliefUpdate
    │   ├── decision.py              # DecisionCreate, DecisionResponse
    │   ├── contradiction.py         # ContradictionResponse, ContradictionResolve
    │   ├── graph.py                 # NodeResponse, EdgeResponse, GraphQuery
    │   ├── snapshot.py              # SnapshotResponse, DeltaResponse
    │   └── compression.py           # CompressionCandidateResponse
    │
    ├── services/                    # Business logic — the actual ATLARS intelligence
    │   ├── capture/
    │   │   ├── text_ingestion.py    # Clean, validate, and store text entries
    │   │   └── voice_transcription.py  # whisperX pipeline: audio → transcript + timestamps
    │   │
    │   ├── synthesis/
    │   │   ├── embedding.py             # nomic-embed-text via OpenRouter
    │   │   ├── trait_extraction.py      # OCEAN signal extraction from entries
    │   │   ├── belief_extraction.py     # Value/belief statement extraction
    │   │   └── contradiction_detection.py  # NLI-style belief pair comparison
    │   │
    │   ├── graph/
    │   │   ├── entity_extraction.py     # GLiNER2: text → typed entities
    │   │   └── graph_builder.py         # Upsert nodes, create edges in MongoDB
    │   │
    │   ├── reflection/
    │   │   ├── domain_scoring.py        # 8-domain health scoring engine
    │   │   ├── snapshot_generator.py    # Build versioned identity snapshots
    │   │   ├── delta_compute.py         # Diff between two snapshots
    │   │   └── focus_recommendations.py  # Generate recommendations from user's own patterns
    │   │
    │   └── routing/
    │       ├── openrouter.py            # OpenRouter async client + model routing table
    │       └── query_router.py          # Context window construction for self-query
    │
    ├── workers/                     # Celery task definitions
    │   ├── celery_app.py            # Celery app init, queue config, Beat schedule
    │   ├── daily_jobs.py            # embed_entry, extract_traits, extract_beliefs, detect_contradictions
    │   ├── weekly_jobs.py           # update_domain_scores, cluster_analysis
    │   └── monthly_jobs.py         # generate_snapshot, generate_compression_candidates, full_synthesis
    │
    └── tests/
        ├── unit/                    # Unit tests — no DB, no network calls
        │   ├── test_auth.py
        │   ├── test_embedding.py
        │   ├── test_trait_extraction.py
        │   ├── test_contradiction_detection.py
        │   └── test_delta_compute.py
        └── integration/             # Integration tests — run against test MongoDB instance
            ├── test_entries_api.py
            ├── test_graph_api.py
            └── test_compression_api.py
```

### Backend Rules

**Where does new code go?**

| What you're adding | Where it goes |
|--------------------|---------------|
| New API route | `app/api/routes/` — one file per resource |
| Request/response schema | `app/models/` — one file per resource |
| Business logic | `app/services/` — organized by pillar |
| Celery task | `app/workers/` — in the correct schedule file |
| Shared utility | `app/core/` — only if it's truly shared infrastructure |

**What NOT to put where:**
- No database queries in `app/api/routes/` — routes call services, services call the DB
- No OpenRouter calls directly in workers — workers call services, services call OpenRouter
- No business logic in `app/models/` — models are schemas only
- No hardcoded strings or prompts inline — prompts live in the service file they belong to

---

## Mobile App

```
mobile/
├── package.json
├── app.json                         # Expo config (app name, bundle ID, icons, splash)
├── tsconfig.json
├── eas.json                         # EAS Build config (build profiles: dev, preview, prod)
│
└── src/
    ├── app/                         # Expo Router — file-based navigation
    │   ├── _layout.tsx              # Root layout (auth guard, navigation stack)
    │   ├── index.tsx                # Onboarding / landing screen
    │   ├── (auth)/
    │   │   ├── login.tsx
    │   │   └── register.tsx
    │   ├── (tabs)/
    │   │   ├── _layout.tsx          # Bottom tab navigator
    │   │   ├── dashboard.tsx        # Domain scores + focus recommendations
    │   │   ├── journal.tsx          # Entry capture — text + voice
    │   │   ├── insights.tsx         # Traits + beliefs + contradictions
    │   │   └── profile.tsx          # Settings, export, compression review
    │   ├── graph.tsx                # Life Graph visualization (full screen)
    │   ├── snapshots.tsx            # Identity snapshots + delta compare
    │   └── query.tsx                # Natural language self-query
    │
    ├── components/
    │   ├── capture/
    │   │   ├── TextEntryInput.tsx   # Text input, char count, submit
    │   │   └── VoiceRecorder.tsx    # expo-av recording → upload
    │   ├── graph/
    │   │   ├── GraphCanvas.tsx      # Force-directed graph (react-native-svg or d3)
    │   │   └── NodeDetail.tsx       # Node tap-through bottom sheet
    │   ├── reflection/
    │   │   ├── DomainRadarChart.tsx
    │   │   ├── DomainScoreCard.tsx
    │   │   ├── SnapshotCard.tsx
    │   │   └── DeltaView.tsx
    │   ├── synthesis/
    │   │   ├── TraitBar.tsx
    │   │   ├── BeliefCard.tsx       # With confirm/reject controls
    │   │   └── ContradictionCard.tsx
    │   └── ui/                      # Shared primitives — no page-specific logic
    │       ├── Button.tsx
    │       ├── Card.tsx
    │       ├── Badge.tsx
    │       └── MaturityBanner.tsx   # "Building your baseline" state UI
    │
    └── lib/
        ├── api.ts                   # API client: base URL, auth headers, token refresh on 401
        ├── auth.ts                  # Secure token storage via expo-secure-store
        └── config.ts                # API_BASE_URL (localhost for dev, prod URL for releases)
```

### Mobile App Rules

**Navigation:**
- Expo Router (file-based) — one file per screen. Screen files go in `src/app/`.
- Tab screens live in `src/app/(tabs)/`. Non-tab full-screen routes sit directly in `src/app/`.

**Component placement:**
- `components/ui/` — only primitives with zero domain knowledge
- `components/capture/`, `components/reflection/`, etc. — components that belong to one ATLARS pillar
- Don't put data-fetching logic inside components — use a `useX` hook or fetch in the screen file

**Token storage:** Use `expo-secure-store`, not `AsyncStorage` or memory. `lib/auth.ts` handles this. Never store tokens anywhere else.

**API base URL:** Read from `lib/config.ts`. In dev it points to `localhost:8000`. In production builds it points to the hosted backend. Never hardcode URLs inline.

---

## Docs

```
docs/
├── ROADMAP.md           # Phase-by-phase build plan — start here if you're new
├── DATA_MODEL.md        # Full MongoDB schema with all fields and indexes
├── API.md               # API contract reference
├── FOLDER_STRUCTURE.md  # This file
└── SELF_HOSTING.md      # (Phase 5) Step-by-step self-hosting guide
```

---

## Scripts

```
scripts/
├── seed_dev.py              # Seeds local MongoDB: creates test user + 30 sample entries
└── setup_atlas_index.py     # One-time: creates Atlas Vector Search index on entries.embedding
```

Run scripts from the `backend/` directory with the virtual environment active.

---

## .github

```
.github/
├── ISSUE_TEMPLATE/
│   ├── bug_report.md        # Required fields: environment, reproduction steps, expected vs actual
│   └── feature_request.md   # Required fields: problem, proposal, which pillar it belongs to
└── PULL_REQUEST_TEMPLATE.md  # Required fields: what changed, how tested, trade-offs
```

---

## Docker Compose

Two files — use the right one:

| File | When to use | MongoDB | Notes |
|------|-------------|---------|-------|
| `docker-compose.dev.yml` | Local development | Local container, `mongodb://mongo:27017` | No Atlas account needed |
| `docker-compose.yml` | Production | Atlas connection string from `.env` | Requires Atlas setup |

**Services in dev compose:**
- `mongo` — MongoDB 7
- `redis` — Redis 7
- `backend` — FastAPI (hot reload)
- `frontend` — Next.js (hot reload)
- `worker` — Celery worker
- `beat` — Celery Beat scheduler
