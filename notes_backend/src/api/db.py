import os
from typing import AsyncGenerator, Optional

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pydantic import BaseModel
from pydantic.fields import Field
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Defaults are sensible for local development; actual values provided via environment in deployment
_DEFAULT_MONGODB_URL = "mongodb://localhost:27017"
_DEFAULT_MONGODB_DB = "notes_app"

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None
_last_connection_error: Optional[str] = None  # track last error for diagnostics


class DBSettings(BaseModel):
    """Database settings loaded from environment."""

    mongodb_url: str = Field(default_factory=lambda: os.getenv("MONGODB_URL", _DEFAULT_MONGODB_URL))
    mongodb_db: str = Field(default_factory=lambda: os.getenv("MONGODB_DB", _DEFAULT_MONGODB_DB))


def _ensure_client() -> AsyncIOMotorClient:
    """
    Ensure a singleton Motor client is initialized.
    Not exposed as public API; used internally by helpers.
    """
    global _client, _db, _last_connection_error
    if _client is None:
        settings = DBSettings()
        # Allow overriding for preview environments if localhost port is remapped
        mongodb_url = settings.mongodb_url
        # Example: if explicitly set to notes_database service through env, we respect it
        try:
            _client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=1500)
            _db = _client[settings.mongodb_db]
            _last_connection_error = None
        except Exception as exc:
            # Do not raise here; keep lazy and record error for later
            _client = None
            _db = None
            _last_connection_error = f"{type(exc).__name__}: {exc}"
    return _client  # may be None if failed


def _ensure_db() -> AsyncIOMotorDatabase:
    """
    Ensure a singleton database reference exists, initializing client if needed.
    """
    _ensure_client()
    assert _db is not None
    return _db


# PUBLIC_INTERFACE
async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Yield the async Motor database instance for dependency injection in routes."""
    db = _ensure_db()
    try:
        yield db
    finally:
        # Do not close here; app lifecycle handles cleanup to keep connection pooling effective.
        pass


# PUBLIC_INTERFACE
def get_notes_collection(db: AsyncIOMotorDatabase = Depends(get_db)) -> AsyncIOMotorCollection:
    """Get the notes collection from the configured database for use in routes/services."""
    return db.get_collection("notes")


# PUBLIC_INTERFACE
async def connect_to_mongo() -> None:
    """Initialize the MongoDB client and database connection.

    This should be called during application startup.
    """
    # Try to initialize but do not crash if server not reachable; lazy connection will be attempted during requests.
    _ensure_client()


# PUBLIC_INTERFACE
async def close_mongo_connection() -> None:
    """Close the MongoDB client connection.

    This should be called during application shutdown to cleanup resources gracefully.
    """
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None
