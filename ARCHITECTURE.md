# ATLARS Architecture

> Adaptive Temporal Life Analysis & Reflection System  
> Architecture Reference — v1.0  
> Maintained by [The Hustle House](https://github.com/TheHustleHouse-HQ) · [TheHustleHouse-HQ/atlars](https://github.com/TheHustleHouse-HQ/atlars)

---

## The Core Problem

Every personal AI tool makes the same mistake: it treats the user as a prompt, not a subject. Nothing accumulates. Nothing learns. The system resets after every session.

The real pain point is **self-opacity**. ATLARS treats a person's inner life as a longitudinal dataset and applies structured analysis to understand patterns, trajectories, and contradictions within that dataset.

---

## The Four Pillars

Every component in ATLARS belongs to exactly one pillar. This is a clean linear pipeline with feedback loops — not a microservices soup.

```
┌─────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   CAPTURE   │ →  │    STORE    │ →  │  SYNTHESIZE  │ →  │   REFLECT   │
│             │    │             │    │              │    │             │
│ Text entry  │    │ MongoDB     │    │ Trait extract│    │ ID snapshot │
│ Voice note  │    │ Atlas       │    │ Contradiction│    │ Evolution   │
│ Micro-entry │    │ Vector      │    │ Delta compute│    │ Focus recs  │
│ Decision log│    │ Search      │    │ Synthesis    │    │ Query self  │
└─────────────┘    └─────────────┘    └──────────────┘    └─────────────┘
```

---

## Personality Framework — Three Layers

### Layer 1 — Scientific Backbone (changes over years)
**Big Five OCEAN**: Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism  
Extracted from natural language using NLP. The slow-moving foundation.

### Layer 2 — Life Domain Health (changes over weeks/months)
Eight domains scored 0–100 on activity level and wellbeing signal:

| Domain | Tracks |
|--------|--------|
| Work | Professional output, motivation, stress |
| Relationships | Depth and quality of close bonds |
| Health | Physical energy, sleep, body |
| Creativity | Making, building, expressing |
| Social | Breadth of social connection |
| Learning | Intellectual growth, curiosity |
| Finance | Economic stability and agency |
| Meaning | Purpose, values alignment |

### Layer 3 — Life Stage (changes over months/years)
Detected from patterns across all layers. Never asked — always inferred. Two levels:
- **Life stage**: broad era (early career, relationship building, creative peak, recovery)
- **Life phase**: specific mode (grind, coasting, expanding, rebuilding, exploring)

---

## Cold-Start Strategy

ATLARS needs data before it can synthesize. Here is exactly what the system does at each maturity stage — and what the user sees at each point:

| Stage | Timeline | System Behavior | UI State |
|-------|----------|-----------------|----------|
| **Baseline** | Day 0–7 | Collect + embed entries only | *"Building your baseline. Keep writing — patterns emerge after 7 days."* |
| **Extraction** | Day 7+ | Trait + belief extraction begins | Traits panel activates, labelled "Early estimate" |
| **Scoring** | Day 30+ | Life domain health scoring begins | Domain dashboard unlocks |
| **Inference** | Day 90+ | Life stage + phase inference begins | Full identity snapshot available |

The system never shows a score it cannot yet compute. The maturity stage is stored per user in the `users` collection and checked before any synthesis job runs.

---

## Data Model

### MongoDB (Primary Store)

All user data lives in a single MongoDB database, partitioned by `user_id`. Two environments:

- **Local dev**: MongoDB runs inside Docker Compose — no account required, zero friction for contributors
- **Production**: MongoDB Atlas with Vector Search enabled

```js
// Core collections
users          // { user_id, email, hashed_password, display_name, created_at,
               //   namespace_config{}, framework_settings{}, maturity_stage }
entries        // { raw_text, timestamp, modality, user_id, session_id,
               //   embedding[], audio_url?, maturity_stage_at_capture }
traits         // { label, ocean_dimension, confidence, first_seen, last_seen, frequency, user_id }
beliefs        // { statement, domain, confidence, date, confirmed_by_user, user_id }
decisions      // { situation, options[], choice, reasoning, outcome, user_id }
snapshots      // { identity_state{}, domains{}, life_stage, life_phase, created_at, user_id }
deltas         // { snapshot_a_id, snapshot_b_id, diff_payload{}, created_at, user_id }
contradictions // { entry_a_id, entry_b_id, belief_ids[], severity, resolved, user_id }

// Life Graph
graph_nodes    // { type: "Person|Place|Project|Event|Emotion|Belief|Goal|Phase",
               //   label, user_id, metadata{}, created_at }
graph_edges    // { from_id, to_id, type, date, weight, user_id }
```

For the full schema with field types, constraints, and example documents see [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md).

### Atlas Vector Search (Semantic Layer)

```
Index on: entries.embedding (1536-dim nomic-embed-text vectors)
Supports: semantic search, temporal filtering, modality filtering
Query pattern: $vectorSearch aggregation pipeline
No separate daemon — embedded in MongoDB Atlas
```

For local development, vector search falls back to cosine similarity computed in Python — no Atlas account needed to contribute.

### Life Graph Queries (Aggregation Pipelines)

```js
// "What was my emotional state around Project X in January?"
db.graph_edges.aggregate([
  { $match: { type: "Emotion→Project", user_id: uid,
              date: { $gte: ISODate("2025-01-01"), $lte: ISODate("2025-01-31") } } },
  { $lookup: { from: "graph_nodes", localField: "from_id",
               foreignField: "_id", as: "emotion_node" } },
  { $lookup: { from: "graph_nodes", localField: "to_id",
               foreignField: "_id", as: "project_node" } }
])
```

---

## The Digital Life Graph

Not a flat list — a graph where nodes are entities from the user's actual life, edges are dated typed relationships, and time is the primary axis. Stored as two MongoDB collections (`graph_nodes` + `graph_edges`) traversed via aggregation pipelines.

**Example edges:**
- `Person → Event`: "Aryan was at the pitch meeting"
- `Emotion → Project`: "I feel anxious about the app launch"
- `Belief → Contradiction → Belief`: "independence matters" conflicts with "I need structure"
- `Phase → Decision`: "During burnout week I quit two commitments"

MongoDB's flexible document model means `metadata{}` on each node type evolves without schema migrations — a `Person` node and a `Project` node carry different fields by design.

---

## Authentication

ATLARS uses **JWT with refresh token rotation**. No session state is stored on the server. Because the client is a mobile app (not a browser), the token storage model differs from a web app.

| Token | Expiry | Storage | Notes |
|-------|--------|---------|-------|
| Access token | 15 min | In-memory (React module-level variable) | Never written to disk — lost on app close |
| Refresh token | 7 days | `expo-secure-store` (iOS Keychain / Android Keystore) | Encrypted OS-level secure storage |

- On app launch, the access token is gone (was in memory). The app reads the refresh token from `expo-secure-store` and silently calls `/auth/refresh` to get a new access token.
- The refresh token is sent as `Authorization: Bearer <refresh_token>` to `/auth/refresh` — not via cookie (cookies are unreliable in React Native).
- On refresh token use, the old token is invalidated and a new one is issued (rotation). The new refresh token is written back to `expo-secure-store`.
- On refresh token expiry, the user is sent back to the login screen.
- All API routes except `/auth/register` and `/auth/login` require `Authorization: Bearer <access_token>`
- Library: `python-jose` + `passlib[bcrypt]`

---

## Job Orchestration

Background processing runs on **Celery with Redis** as the message broker. Three queues map to the three processing schedules.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐
│  FastAPI app │ ──► │  Redis       │ ──► │  Celery Workers          │
│              │     │  (broker +   │     │                          │
│ Entry saved  │     │   result     │     │  daily_queue:            │
│ → enqueue    │     │   backend)   │     │    embed_new_entries      │
│   embed_entry│     │              │     │    extract_traits         │
│   task       │     │              │     │    extract_beliefs        │
│              │     │              │     │    detect_contradictions   │
│ Celery Beat  │     │              │     │                          │
│ (scheduler)  │     │              │     │  weekly_queue:           │
│ → triggers   │     │              │     │    cluster_analysis       │
│   scheduled  │     │              │     │    update_domain_scores   │
│   jobs       │     │              │     │                          │
│              │     │              │     │  monthly_queue:          │
│              │     │              │     │    full_synthesis         │
│              │     │              │     │    compression_candidates │
└──────────────┘     └──────────────┘     └──────────────────────────┘
```

Everything is defined in code — no OS cron, no external scheduler. Both Redis and the Celery worker run inside Docker Compose in development.

---

## OpenRouter Model Routing

Cost is a design constraint. 80%+ of processing runs on free-tier models.

| Task | Model | Frequency |
|------|-------|-----------|
| Embedding generation | nomic-embed-text (free) | Every entry |
| Trait/belief extraction | Gemini Flash / Llama 3.1 8B | Daily |
| Contradiction detection | Gemini Flash / Mistral 7B | Daily |
| Weekly synthesis | Claude Haiku / Gemini Pro | Weekly |
| Deep insight reports | Claude Sonnet | Monthly only |
| User query responses | Llama 3.1 70B | On-demand |

**Estimated cost**: $0.50–$2.00/user/month for active daily users.

---

## Context Compression Protocol

After one year of daily journaling, raw entries exceed any LLM context window. The solution is tiered memory with user-controlled compression review.

| Tier | Data | Age | Format | User control |
|------|------|-----|--------|--------------| 
| Hot | Raw entries | 0–30 days | Full text + embeddings | Read / edit / delete |
| Warm | Monthly summaries | 1–12 months | Structured summary | Review before compress |
| Cold | Quarterly summaries | 1–3 years | High-level synthesis | Review once per quarter |
| Permanent | "Always remember" items | Any age | Full fidelity | User explicitly marks |

**Key rule**: Compression is never automatic. The user reviews and approves every summary before raw data is archived. The user can mark any entry as `permanent: true` — exempt from all compression forever.

---

## Processing Schedule

- **Daily** — embed new entries, extract traits/beliefs, run contradiction check
- **Weekly** — cluster analysis, domain score update, snapshot delta compute
- **Monthly** — complete identity re-synthesis, compression candidate generation, evolution report

---

## Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| Backend | FastAPI (Python) | Async, fast, excellent ML ecosystem |
| Database (dev) | MongoDB in Docker | Zero friction — no account required for contributors |
| Database (prod) | MongoDB Atlas | Flexible documents, horizontal scale, no migrations |
| Vector Search | MongoDB Atlas Vector Search | Built into the DB — no separate vector daemon |
| Life Graph | MongoDB (graph_nodes + graph_edges) | Native doc model, aggregation pipeline traversals |
| Job Queue | Celery + Redis | Python-native, battle-tested async task processing |
| Transcription | whisperX | Word-level timestamps, VAD preprocessing, 70x realtime |
| Entity Extraction | GLiNER2 | Zero-shot, CPU-native, dynamic schema at inference |
| Embeddings | nomic-embed-text via OpenRouter | Free, high quality |
| LLM Routing | OpenRouter | Unified API, multi-model, cost optimization |
| Auth | JWT + refresh tokens (Bearer) | Stateless, works identically for mobile clients |
| Mobile App | React Native (Expo) | Single codebase for iOS + Android |
| Distribution | Apple App Store + Google Play Store | Standard mobile distribution |
| Backend Deployment | Docker Compose on cloud VPS | Single command, self-hostable |

---

## Deployment Models & Privacy

ATLARS ships as a **mobile app** (iOS + Android) backed by a cloud API. The codebase is open source and supports two backend deployment models:

### 1. Hosted App (Cloud) — Default for End Users
The managed product maintained by The Hustle House. Users download ATLARS from the App Store or Play Store and connect to the hosted backend.
- **Backups & Recovery:** Handled automatically via MongoDB Atlas cloud backups. If a user loses their device, their data is safe in the cloud.
- **System Improvement:** We collect anonymized, aggregated metadata (e.g., contradiction detection success rates, pipeline bottlenecks) to improve our prompts and scoring engines. We do **not** train foundational LLM weights on raw personal journals.
- **Encryption:** Encrypted at rest via Atlas default encryption.

### 2. Self-Hosted Backend (Open Source)
Technical users can run the backend on their own VPS via Docker Compose and point the mobile app at their own server via a custom API URL in settings.
- **Backups & Recovery:** The user owns their infrastructure. The system provides a raw JSON export tool, but database backup is the user's responsibility.
- **System Improvement:** 100% offline and air-gapped by default. Zero telemetry or training data is sent to The Hustle House.
- **Encryption:** Handled by the host machine's volume encryption.

### Mobile App Architecture
The React Native (Expo) mobile app communicates exclusively through the REST API defined in [`docs/API.md`](docs/API.md). The app itself contains no business logic — all intelligence lives in the backend. This clean separation means:
- Contributors can build backend features and test them via the API without touching the mobile app
- The mobile app can be pointed at any backend instance (hosted or self-hosted) via an API URL setting
- The same backend serves both the hosted product and self-hosters

Across all deployment models, **User Namespace Isolation** is hardcoded into the API layer — all queries are partitioned by `user_id`, making cross-user data leakage architecturally impossible.

---

## What We Build vs. Wire

| Component | Approach | Why |
|-----------|----------|-----|
| MongoDB Atlas + Vector Search | Wire | Zero-ops, unified DB + vector layer |
| whisperX transcription | Wire | Production-ready, 70x realtime |
| GLiNER2 entity extraction | Wire | Zero-shot, no retraining needed |
| Celery + Redis | Wire | Battle-tested job orchestration |
| Life domain scoring engine | Build | Core ATLARS logic |
| Contradiction detection pipeline | Build | Novel framing of NLI |
| Focus recommendation system | Build | Key differentiator |
| Context compression + review UI | Build | No tool does this right |
| OpenRouter routing layer | Build | Custom cost-optimization logic |
| Graph traversal query engine | Build | MongoDB aggregation pipelines for temporal queries |
| Year-in-review narrative export | Build | Unique output format |
| JWT auth layer | Build | Standard but must be implemented correctly |

---

## What ATLARS Is Not

Explicit scope boundaries so contributors don't build the wrong thing:

- **Not a chatbot wrapper** — the interface is not a general-purpose chat UI
- **Not a content tool** — ATLARS does not generate content in the user's voice or for external publishing
- **Not a social platform** — no sharing, no public profiles, no feeds
- **Not engagement-optimized** — no streaks, no notifications designed to pull users back, no time-on-app metrics

---

*For full MongoDB schema and indexes, see [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md).*  
*For API contract reference, see [`docs/API.md`](docs/API.md).*  
*For codebase folder structure, see [`docs/FOLDER_STRUCTURE.md`](docs/FOLDER_STRUCTURE.md).*  
*For the phased build roadmap, see [`docs/ROADMAP.md`](docs/ROADMAP.md).*
