"""
Seed local MongoDB with a test user and 30 sample entries.
Run from the backend/ directory with the virtual environment active:
    python ../scripts/seed_dev.py

Idempotent — safe to run multiple times.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
import random

from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt as _bcrypt

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "atlars"
TEST_EMAIL = "test@atlars.dev"
TEST_PASSWORD = "testpassword"
TEST_DISPLAY_NAME = "Test User"


def _hash(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()

SAMPLE_ENTRIES = [
    "Had a really productive morning. Finished the backend auth flow and it feels solid.",
    "Struggling to focus today. Keep getting distracted by small tasks instead of the big ones.",
    "Good conversation with the team about product direction. Starting to feel aligned.",
    "Feeling burned out. Three weeks of intense work and I haven't taken a real break.",
    "Read for two hours this evening. Forgot how much I enjoy it when I actually make time.",
    "Difficult decision today — turned down a project that paid well but didn't excite me.",
    "Went for a long walk. Cleared my head. Sometimes stepping away is the most productive thing.",
    "Relationship with my co-founder feels strained lately. Need to have an honest conversation.",
    "Creative block all week. Nothing I make feels good enough to ship.",
    "Breakthrough moment on the data model. The graph structure finally clicked.",
    "Slept 9 hours for the first time in weeks. Feel like a different person.",
    "Had to say no to a friend's request. Felt guilty but I know it was the right call.",
    "Learning Rust on the side. Completely different mental model — enjoying the challenge.",
    "Retrospective today. The team pointed out I interrupt people in meetings. Hard to hear but true.",
    "Finances are tighter than I'd like. Stress is affecting my sleep.",
    "Shipped a small feature I'm genuinely proud of. Users responded well.",
    "Thinking about the next 5 years. Not sure what I actually want, which is unsettling.",
    "Great workout. Exercise has been the one consistent thing keeping me sane.",
    "Helped a junior developer debug a tricky async issue. Reminded me I enjoy mentoring.",
    "Caught myself being pessimistic in a planning meeting. I need to watch that pattern.",
    "Spent the afternoon on a creative side project. No pressure, no deadline. It was great.",
    "Conflict with a client over scope. Held my ground. They respected it in the end.",
    "Feeling grateful today. The team is exceptional and I don't say that enough.",
    "Three hours lost to meetings that could have been emails. Need to protect my deep work time.",
    "Had an honest conversation with my co-founder. Cleared the air. Should have done it sooner.",
    "Milestone reached — first 100 users. Small number but it feels real now.",
    "Took the weekend completely off. No laptop, no Slack. Highly recommend.",
    "Thinking about independence vs structure. I say I want freedom but I work best with constraints.",
    "Deep work session — 4 hours of uninterrupted coding. This is what I live for.",
    "Reflecting on the last 6 months. More progress than I give myself credit for.",
]


async def seed():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    users = db["users"]
    entries = db["entries"]

    # Upsert test user
    existing = await users.find_one({"email": TEST_EMAIL})
    if existing:
        user_id = existing["user_id"]
        print(f"User already exists: {TEST_EMAIL} (user_id: {user_id})")
    else:
        user_id = str(uuid.uuid4())
        now = datetime.utcnow()
        user_doc = {
            "user_id": user_id,
            "email": TEST_EMAIL,
            "hashed_password": _hash(TEST_PASSWORD),
            "display_name": TEST_DISPLAY_NAME,
            "created_at": now,
            "last_active_at": now,
            "maturity_stage": "baseline",
            "entry_count": 0,
            "first_entry_at": None,
            "namespace_config": {"compression_enabled": True, "data_retention_days": None},
            "framework_settings": {"ocean_enabled": True, "domain_scoring_enabled": True, "life_stage_enabled": True},
            "active_refresh_token_ids": [],
        }
        await users.insert_one(user_doc)
        print(f"Created user: {TEST_EMAIL} (user_id: {user_id})")

    # Check existing entries
    existing_count = await entries.count_documents({"user_id": user_id})
    if existing_count >= 30:
        print(f"Entries already seeded ({existing_count} found). Skipping.")
        client.close()
        return

    # Seed 30 entries spread over the past 60 days
    now = datetime.utcnow()
    entry_docs = []
    for i, text in enumerate(SAMPLE_ENTRIES):
        days_ago = random.randint(1, 60)
        hours_ago = random.randint(0, 23)
        timestamp = now - timedelta(days=days_ago, hours=hours_ago)
        entry_docs.append({
            "entry_id": str(uuid.uuid4()),
            "user_id": user_id,
            "raw_text": text,
            "timestamp": timestamp,
            "modality": "text",
            "session_id": None,
            "embedding": None,
            "embedding_generated_at": None,
            "audio_url": None,
            "word_timestamps": None,
            "compression_tier": "hot",
            "compression_candidate_id": None,
            "maturity_stage_at_capture": "baseline",
        })

    await entries.insert_many(entry_docs)
    await users.update_one(
        {"user_id": user_id},
        {"$set": {"entry_count": 30, "first_entry_at": min(e["timestamp"] for e in entry_docs)}},
    )

    print(f"Seeded 30 entries for {TEST_EMAIL}")
    print(f"\nLogin credentials:")
    print(f"  Email:    {TEST_EMAIL}")
    print(f"  Password: {TEST_PASSWORD}")
    print(f"  API:      http://localhost:8000/docs")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
