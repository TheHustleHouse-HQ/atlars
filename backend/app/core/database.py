from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

_client: AsyncIOMotorClient | None = None


async def connect_db() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.mongo_url)
    # Verify connection
    await _client.admin.command("ping")


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        _client = None


def get_database() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _client[settings.mongo_db_name]


# Typed collection accessors — use these everywhere, never raw collection names
def get_users_collection():
    return get_database()["users"]


def get_entries_collection():
    return get_database()["entries"]


def get_traits_collection():
    return get_database()["traits"]


def get_beliefs_collection():
    return get_database()["beliefs"]


def get_decisions_collection():
    return get_database()["decisions"]


def get_contradictions_collection():
    return get_database()["contradictions"]


def get_snapshots_collection():
    return get_database()["snapshots"]


def get_deltas_collection():
    return get_database()["deltas"]


def get_graph_nodes_collection():
    return get_database()["graph_nodes"]


def get_graph_edges_collection():
    return get_database()["graph_edges"]
