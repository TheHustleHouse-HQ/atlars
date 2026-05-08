# ATLARS API Reference

> API contract for the ATLARS backend.  
> Base URL (local dev): `http://localhost:8000`  
> All endpoints return JSON. All authenticated endpoints require `Authorization: Bearer <access_token>`.

---

## Conventions

### Authentication

```http
Authorization: Bearer <access_token>
```

Access tokens are obtained from `/auth/login` or `/auth/refresh`. They expire in 15 minutes.

Refresh tokens are returned in the JSON response body and stored by the mobile client in `expo-secure-store` (iOS Keychain / Android Keystore). The client sends the refresh token explicitly as `Authorization: Bearer <refresh_token>` when calling `/auth/refresh`. There are no cookies — this is a mobile API.

### Standard Error Response

```json
{
  "error": {
    "code": "BELIEF_NOT_FOUND",
    "message": "No belief with ID abc123 found for this user.",
    "status": 404
  }
}
```

### Pagination

Endpoints that return lists use cursor-based pagination:

```http
GET /entries/?limit=20&cursor=<entry_id>
```

Response includes `next_cursor` (null if no more results).

### Maturity Gate Errors

Endpoints that require a certain maturity stage return `423 Locked` if the user hasn't reached it yet:

```json
{
  "error": {
    "code": "MATURITY_GATE",
    "message": "This feature requires at least 7 days of entries. You are on day 3.",
    "status": 423,
    "current_stage": "baseline",
    "required_stage": "extraction"
  }
}
```

---

## Auth Routes

### POST /auth/register

Creates a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "minimum8chars",
  "display_name": "Your Name"
}
```

**Response: 201 Created**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "user_id": "550e8400-...",
    "email": "user@example.com",
    "display_name": "Your Name",
    "maturity_stage": "baseline"
  }
}
```

Client must store `refresh_token` in `expo-secure-store` immediately. It is not re-issued except on `/auth/refresh`.

**Errors:** `409` email already registered · `422` validation error

---

### POST /auth/login

**Request:**
```json
{ "email": "user@example.com", "password": "yourpassword" }
```

**Response: 200 OK** — same shape as `/auth/register` (includes both `access_token` and `refresh_token`)

**Errors:** `401` invalid credentials · `429` rate limited (5 attempts/min)

---

### POST /auth/refresh

Uses the refresh token (from `expo-secure-store`) to issue a new access token.

**Request:**
```http
Authorization: Bearer <refresh_token>
```

**Response: 200 OK**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

Both tokens are rotated — old refresh token is invalidated. Client must overwrite the stored refresh token in `expo-secure-store` with the new one.

**Errors:** `401` invalid or expired refresh token

---

### POST /auth/logout

Invalidates the refresh token server-side.

**Request:**
```http
Authorization: Bearer <refresh_token>
```

**Response: 204 No Content**

Client must also delete the refresh token from `expo-secure-store` and clear the in-memory access token.

---

## Entries Routes

All routes require authentication.

### POST /entries/

Submit a text entry.

**Request:**
```json
{
  "raw_text": "Had a tough meeting today. Feeling like the project direction is unclear.",
  "modality": "text",
  "session_id": null
}
```

**Response: 201 Created**
```json
{
  "entry_id": "...",
  "raw_text": "Had a tough meeting today...",
  "modality": "text",
  "timestamp": "2025-05-08T10:30:00Z",
  "embedding_generated_at": null,
  "compression_tier": "hot"
}
```

Embedding is generated asynchronously. `embedding_generated_at` is null until the Celery job completes.

---

### POST /entries/voice

Upload a voice note.

**Request:** `multipart/form-data`
- `audio`: audio file (mp3, wav, m4a, webm — max 25MB)
- `session_id`: optional string

**Response: 202 Accepted** — entry created, transcription running asynchronously
```json
{
  "entry_id": "...",
  "modality": "voice",
  "status": "transcribing",
  "timestamp": "2025-05-08T10:31:00Z"
}
```

---

### GET /entries/

Returns paginated list of user's entries.

**Query params:**
- `limit` (int, default 20, max 100)
- `cursor` (entry_id, for pagination)
- `modality` (text \| voice \| decision \| micro — optional filter)

**Response: 200 OK**
```json
{
  "entries": [ { "entry_id": "...", "raw_text": "...", "timestamp": "...", "modality": "text" } ],
  "next_cursor": "entry_id_or_null"
}
```

---

### GET /entries/{entry_id}

Returns a single entry with all fields including embedding status.

**Response: 200 OK** · **Errors:** `404`

---

### PATCH /entries/{entry_id}

Edit an entry's raw_text. Re-triggers embedding generation.

**Request:** `{ "raw_text": "corrected text" }`  
**Response: 200 OK** — updated entry  
**Errors:** `404` · `403` not owner

---

### DELETE /entries/{entry_id}

Permanently deletes the entry and its embedding.

**Response: 204 No Content**  
**Errors:** `404` · `403` not owner

---

### POST /entries/search

Semantic search over user's entries.

**Request:**
```json
{ "query": "times I felt anxious about work", "limit": 10 }
```

**Response: 200 OK**
```json
{
  "results": [
    { "entry_id": "...", "raw_text": "...", "timestamp": "...", "similarity_score": 0.87 }
  ]
}
```

**Maturity gate:** requires `extraction` stage (7+ days of embedded entries)

---

## Graph Routes

### GET /graph/nodes

**Query params:** `type` (Person \| Place \| Project \| Event \| Emotion \| Belief \| Goal \| Phase)  
**Maturity gate:** `extraction`

**Response: 200 OK**
```json
{
  "nodes": [
    { "node_id": "...", "type": "Person", "label": "Aryan", "mention_count": 12,
      "first_mentioned": "2025-01-15T...", "last_mentioned": "2025-05-01T..." }
  ]
}
```

---

### GET /graph/edges

**Query params:** `type`, `from_date`, `to_date`, `from_id`, `to_id`  
**Response: 200 OK** — list of edges with `from_id`, `to_id`, `type`, `date`, `weight`

---

### POST /graph/query

Natural language temporal graph query.

**Request:**
```json
{ "question": "Who was I working with most in March?" }
```

**Response: 200 OK**
```json
{
  "answer": "Based on your entries in March, you worked most frequently with Aryan (8 entries) and Priya (5 entries) on the app launch project.",
  "nodes_referenced": [ { "node_id": "...", "label": "Aryan", "type": "Person" } ],
  "entries_used": [ "entry_id_1", "entry_id_2" ]
}
```

**Maturity gate:** `extraction`

---

## Traits Routes

### GET /traits/

Returns user's extracted OCEAN traits ordered by confidence.

**Maturity gate:** `extraction`

**Response: 200 OK**
```json
{
  "traits": [
    { "trait_id": "...", "label": "high openness to experience",
      "ocean_dimension": "O", "direction": "high",
      "confidence": 0.82, "signal_count": 34,
      "first_seen": "2025-05-08T...", "last_seen": "2025-05-08T..." }
  ],
  "is_early_estimate": true
}
```

`is_early_estimate` is `true` until Day 30.

---

## Beliefs Routes

### GET /beliefs/

**Query params:** `domain`, `confirmed` (true \| false \| null), `limit`, `cursor`  
**Maturity gate:** `extraction`

---

### PATCH /beliefs/{belief_id}

User confirms, edits, or rejects a belief.

**Request:**
```json
{ "confirmed_by_user": true, "statement": "optional edited statement" }
```

**Response: 200 OK** — updated belief

---

## Contradictions Routes

### GET /contradictions/

**Query params:** `resolved` (boolean), `min_severity` (0.0–1.0)  
**Maturity gate:** `extraction`

---

### PATCH /contradictions/{contradiction_id}/resolve

**Request:** `{ "resolution_note": "These apply in different contexts." }`  
**Response: 200 OK**

---

## Snapshots Routes

### GET /snapshots/

Returns list of identity snapshots with date and summary.  
**Maturity gate:** `scoring` (Day 30+)

---

### GET /snapshots/{snapshot_id}

Returns full snapshot with all fields.

---

### GET /snapshots/{snapshot_id}/compare/{snapshot_id_2}

Returns a delta document between two snapshots.

**Response: 200 OK**
```json
{
  "delta_id": "...",
  "period_a": "2025-01-01T...",
  "period_b": "2025-04-01T...",
  "ocean_changes": [ { "dimension": "O", "from": 0.72, "to": 0.81, "delta": +0.09 } ],
  "domain_changes": [ { "domain": "Creativity", "activity_delta": -23, "wellbeing_delta": -18 } ],
  "new_beliefs": [ { "statement": "I work better alone on creative projects" } ],
  "dropped_beliefs": [],
  "life_stage_change": null
}
```

---

## Query Route

### POST /query/

Ask a natural language question about yourself.

**Request:**
```json
{ "question": "What patterns do I have around quitting things?" }
```

**Response: 200 OK**
```json
{
  "answer": "Across your entries, you've quit or stepped back from commitments 4 times — all during periods where your Work domain score dropped below 40. The pattern suggests capacity constraints, not lack of interest.",
  "source_entry_ids": ["entry_id_1", "entry_id_2", "entry_id_3"],
  "query_id": "..."
}
```

**Maturity gate:** `extraction`

---

## Compression Routes

### GET /compression/candidates/

Returns entries pending user review for compression.

**Response: 200 OK**
```json
{
  "candidates": [
    {
      "candidate_id": "...",
      "period": { "start": "2024-11-01T...", "end": "2024-11-30T..." },
      "proposed_summary": "November was dominated by project launch stress...",
      "entry_count": 42,
      "entries": [ { "entry_id": "...", "raw_text": "...", "timestamp": "..." } ]
    }
  ]
}
```

---

### POST /compression/approve/{candidate_id}

Approves the summary. Raw entries are archived to Warm tier.  
**Response: 204 No Content**

---

### POST /compression/reject/{candidate_id}

Rejects the summary. Entries stay Hot. Not re-proposed for 90 days.  
**Response: 204 No Content**

---

### PATCH /entries/{entry_id}/permanent

Marks an entry as permanently exempt from all compression.  
**Request:** `{ "permanent": true }`  
**Response: 200 OK**

---

## Exports Routes

### GET /exports/full

Downloads the user's complete dataset as structured JSON.

**Response:** `application/json` file download  
Includes all entries, traits, beliefs, decisions, contradictions, snapshots, deltas, graph nodes, graph edges.

---

### POST /exports/year-in-review

Triggers Claude Sonnet synthesis of the past 12 months.

**Response: 202 Accepted** — job enqueued, result delivered via webhook or polling  
**Maturity gate:** `inference` (Day 90+, at least one full year of data)

---

## Recommendations Route

### GET /recommendations/

Returns current week's focus recommendations.

**Response: 200 OK**
```json
{
  "recommendations": [
    {
      "domain": "Creativity",
      "observation": "Your Creativity domain has dropped 40 points in 3 weeks.",
      "pattern": "Your highest-output creative entries cluster on Tuesday mornings.",
      "suggestion": "Block Tuesday mornings — your data says that's when it works."
    }
  ],
  "generated_at": "2025-05-05T00:00:00Z"
}
```

**Maturity gate:** `scoring` (Day 30+)
