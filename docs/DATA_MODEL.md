# ATLARS Data Model

> Full MongoDB schema reference for ATLARS.  
> Every collection, every field, every index.  
> For architecture context, see [`ARCHITECTURE.md`](../ARCHITECTURE.md).

---

## Environments

| Environment | Database | Notes |
|-------------|----------|-------|
| Local dev | MongoDB in Docker (`docker-compose.dev.yml`) | No account required, `mongodb://localhost:27017` |
| Production | MongoDB Atlas | Atlas Vector Search required for semantic queries |

Database name: `atlars`  
All data is partitioned by `user_id`. Cross-user queries are impossible by application design.

---

## Collections

### `users`

Stores account credentials and per-user system configuration.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | auto | MongoDB document ID |
| `user_id` | UUID string | yes | Application-level unique identifier, used as partition key everywhere |
| `email` | string | yes | Unique, lowercase, indexed |
| `hashed_password` | string | yes | bcrypt hash — never stored in plaintext |
| `display_name` | string | yes | User-chosen display name |
| `created_at` | ISODate | yes | Account creation timestamp |
| `last_active_at` | ISODate | yes | Updated on every authenticated request |
| `maturity_stage` | string | yes | `"baseline"` \| `"extraction"` \| `"scoring"` \| `"inference"` |
| `entry_count` | number | yes | Running count, used to determine maturity stage transitions |
| `first_entry_at` | ISODate \| null | yes | Date of first entry, null until first entry submitted |
| `namespace_config` | object | yes | See sub-fields below |
| `framework_settings` | object | yes | See sub-fields below |

**`namespace_config` sub-fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `compression_enabled` | boolean | `true` | Whether this user participates in compression |
| `data_retention_days` | number \| null | `null` | null = keep forever |

**`framework_settings` sub-fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ocean_enabled` | boolean | `true` | Whether OCEAN trait extraction runs for this user |
| `domain_scoring_enabled` | boolean | `true` | Whether life domain scoring runs |
| `life_stage_enabled` | boolean | `true` | Whether life stage inference runs |

**Indexes:**
```js
{ email: 1 }           // unique
{ user_id: 1 }         // unique
```

**Example document:**
```json
{
  "_id": "ObjectId(...)",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "sourabh@thehustlehouseofficial.com",
  "hashed_password": "$2b$12$...",
  "display_name": "Sourabh",
  "created_at": "2025-05-08T05:00:00Z",
  "last_active_at": "2025-05-08T10:00:00Z",
  "maturity_stage": "baseline",
  "entry_count": 3,
  "first_entry_at": "2025-05-08T06:00:00Z",
  "namespace_config": { "compression_enabled": true, "data_retention_days": null },
  "framework_settings": { "ocean_enabled": true, "domain_scoring_enabled": true, "life_stage_enabled": true }
}
```

---

### `entries`

The primary data source. Every piece of text or voice note the user submits.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | auto | MongoDB document ID |
| `entry_id` | UUID string | yes | Application-level ID |
| `user_id` | UUID string | yes | Owner — partition key |
| `raw_text` | string | yes | Full text of the entry (for voice: the transcript) |
| `timestamp` | ISODate | yes | When the entry was submitted |
| `modality` | string | yes | `"text"` \| `"voice"` \| `"decision"` \| `"micro"` |
| `session_id` | UUID string \| null | no | Groups entries from the same session |
| `embedding` | number[] | no | 1536-dim nomic-embed-text vector. Set async after entry is saved. |
| `embedding_generated_at` | ISODate \| null | no | null until embedding job completes |
| `audio_url` | string \| null | no | Object storage URL for original audio (voice entries only) |
| `word_timestamps` | object[] \| null | no | whisperX word-level timestamps (voice entries only) |
| `compression_tier` | string | yes | `"hot"` \| `"warm"` \| `"cold"` \| `"permanent"` |
| `compression_candidate_id` | ObjectId \| null | no | Links to the compression candidate that archived this entry |
| `maturity_stage_at_capture` | string | yes | The user's maturity stage when this entry was captured |

**Indexes:**
```js
{ user_id: 1, timestamp: -1 }     // primary query pattern (user's entries, newest first)
{ user_id: 1, modality: 1 }       // filter by modality
{ user_id: 1, compression_tier: 1 } // compression queries
{ entry_id: 1 }                    // unique
```

**Atlas Vector Search index** (production only):
```json
{
  "collectionName": "entries",
  "database": "atlars",
  "type": "vectorSearch",
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1536,
      "similarity": "cosine"
    },
    { "type": "filter", "path": "user_id" },
    { "type": "filter", "path": "timestamp" },
    { "type": "filter", "path": "modality" }
  ]
}
```

---

### `traits`

OCEAN trait signals extracted from entries. Updated by the daily job.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | auto | |
| `trait_id` | UUID string | yes | |
| `user_id` | UUID string | yes | Partition key |
| `label` | string | yes | Human-readable trait label (e.g. "high openness to experience") |
| `ocean_dimension` | string | yes | `"O"` \| `"C"` \| `"E"` \| `"A"` \| `"N"` |
| `direction` | string | yes | `"high"` \| `"low"` |
| `confidence` | number | yes | 0.0–1.0 — aggregate confidence across all signals |
| `signal_count` | number | yes | Number of entries that contributed to this trait |
| `first_seen` | ISODate | yes | Date of first entry that contributed |
| `last_seen` | ISODate | yes | Date of most recent contributing entry |
| `updated_at` | ISODate | yes | Last time the daily job updated this record |

**Indexes:**
```js
{ user_id: 1, ocean_dimension: 1 }
{ user_id: 1, confidence: -1 }
```

---

### `beliefs`

Value statements and beliefs extracted from entries.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | auto | |
| `belief_id` | UUID string | yes | |
| `user_id` | UUID string | yes | Partition key |
| `statement` | string | yes | The extracted belief in natural language |
| `domain` | string | yes | Which life domain this belief relates to (Work, Relationships, Health, etc.) or `"general"` |
| `confidence` | number | yes | 0.0–1.0 — extraction confidence |
| `confirmed_by_user` | boolean \| null | yes | `null` = not yet reviewed, `true` = confirmed, `false` = rejected |
| `source_entry_ids` | UUID string[] | yes | Entries this belief was extracted from |
| `first_seen` | ISODate | yes | |
| `last_seen` | ISODate | yes | |

**Indexes:**
```js
{ user_id: 1, domain: 1 }
{ user_id: 1, confirmed_by_user: 1 }
```

---

### `decisions`

Explicit decision logs. User-submitted, not extracted.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | auto | |
| `decision_id` | UUID string | yes | |
| `user_id` | UUID string | yes | Partition key |
| `situation` | string | yes | Description of the context |
| `options` | string[] | yes | Options that were considered |
| `choice` | string | yes | What was chosen |
| `reasoning` | string | no | Why — optional |
| `outcome` | string | no | Updated later when the outcome is known |
| `timestamp` | ISODate | yes | When the decision was made |

---

### `contradictions`

Pairs of beliefs or entries flagged as semantically inconsistent.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | auto | |
| `contradiction_id` | UUID string | yes | |
| `user_id` | UUID string | yes | Partition key |
| `belief_a_id` | UUID string | yes | First belief |
| `belief_b_id` | UUID string | yes | Contradicting belief |
| `explanation` | string | yes | System-generated explanation of why these conflict |
| `severity` | number | yes | 0.0–1.0 — how strongly they conflict |
| `resolved` | boolean | yes | Whether the user has marked this as understood |
| `resolution_note` | string \| null | no | User-written note explaining their understanding |
| `detected_at` | ISODate | yes | |

**Indexes:**
```js
{ user_id: 1, resolved: 1, severity: -1 }
```

---

### `snapshots`

Versioned identity state at a point in time. Generated monthly by the Celery job.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | auto | |
| `snapshot_id` | UUID string | yes | |
| `user_id` | UUID string | yes | Partition key |
| `created_at` | ISODate | yes | When this snapshot was generated |
| `period_start` | ISODate | yes | Start of the period this snapshot covers |
| `period_end` | ISODate | yes | End of the period |
| `ocean_scores` | object | yes | `{ O, C, E, A, N }` each with `score` and `confidence` |
| `domain_scores` | object | yes | `{ Work, Relationships, Health, ... }` each with `activity` and `wellbeing` |
| `life_stage` | string \| null | yes | Current life stage (null until Day 90) |
| `life_phase` | string \| null | yes | Current life phase (null until Day 90) |
| `top_beliefs` | object[] | yes | Top 5 confirmed beliefs at time of snapshot |
| `active_traits` | object[] | yes | Top 5 traits by confidence at time of snapshot |
| `entry_count_in_period` | number | yes | How many entries contributed to this snapshot |

---

### `deltas`

Diff between two snapshots.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | auto | |
| `delta_id` | UUID string | yes | |
| `user_id` | UUID string | yes | Partition key |
| `snapshot_a_id` | UUID string | yes | Earlier snapshot |
| `snapshot_b_id` | UUID string | yes | Later snapshot |
| `ocean_changes` | object | yes | Per-dimension: `{ dimension, from, to, delta }` |
| `domain_changes` | object[] | yes | Per-domain: `{ domain, activity_delta, wellbeing_delta }` |
| `new_beliefs` | object[] | yes | Beliefs present in B but not A |
| `dropped_beliefs` | object[] | yes | Beliefs present in A but not B |
| `life_stage_change` | object \| null | no | `{ from, to }` if life stage changed |
| `created_at` | ISODate | yes | |

---

### `graph_nodes`

Entities from the user's life.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | auto | |
| `node_id` | UUID string | yes | |
| `user_id` | UUID string | yes | Partition key |
| `type` | string | yes | `"Person"` \| `"Place"` \| `"Project"` \| `"Event"` \| `"Emotion"` \| `"Belief"` \| `"Goal"` \| `"Phase"` |
| `label` | string | yes | Human-readable name (e.g. "Aryan", "the app launch", "anxiety") |
| `metadata` | object | no | Flexible per type — see below |
| `mention_count` | number | yes | How many times this entity has appeared in entries |
| `first_mentioned` | ISODate | yes | |
| `last_mentioned` | ISODate | yes | |
| `created_at` | ISODate | yes | |

**`metadata` by node type:**
- `Person`: `{ relationship_type }` (colleague, friend, family, etc.)
- `Project`: `{ status }` (active, completed, abandoned)
- `Emotion`: `{ valence }` (positive, negative, neutral)
- `Goal`: `{ status, target_date }` (active, achieved, dropped)

**Indexes:**
```js
{ user_id: 1, type: 1 }
{ user_id: 1, label: "text" }   // text search on label
```

---

### `graph_edges`

Typed, dated relationships between nodes.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | auto | |
| `edge_id` | UUID string | yes | |
| `user_id` | UUID string | yes | Partition key |
| `from_id` | UUID string | yes | Source node_id |
| `to_id` | UUID string | yes | Target node_id |
| `type` | string | yes | Relationship type — see taxonomy below |
| `date` | ISODate | yes | When this relationship was active |
| `weight` | number | yes | 0.0–1.0 — strength/confidence of this edge |
| `source_entry_id` | UUID string | yes | The entry this edge was extracted from |

**Edge type taxonomy:**
```
Person   → Event        : "attended"
Person   → Project      : "worked_on"
Person   → Phase        : "present_during"
Emotion  → Project      : "felt_about"
Emotion  → Person       : "felt_toward"
Emotion  → Event        : "felt_during"
Belief   → Contradiction → Belief  : "contradicts"
Phase    → Decision     : "context_of"
Goal     → Phase        : "active_during"
```

**Indexes:**
```js
{ user_id: 1, from_id: 1 }
{ user_id: 1, to_id: 1 }
{ user_id: 1, type: 1, date: -1 }
```
