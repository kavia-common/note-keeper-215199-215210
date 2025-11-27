import os
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, Depends, Path, Body, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from src.api.db import (
    connect_to_mongo,
    close_mongo_connection,
    get_notes_collection,
    get_db,
)
from src.api.models import (
    NoteIn,
    NoteOut,
    NoteUpdate,
    mongo_doc_to_note_out,
    note_in_to_mongo_doc,
    apply_note_update,
)

openapi_tags = [
    {"name": "health", "description": "Service health and readiness endpoints."},
    {"name": "notes", "description": "Operations related to notes resources."},
]

app = FastAPI(
    title="Notes Backend API",
    description="REST API for the Notes application, providing CRUD operations for notes.",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# Configure CORS using env FRONTEND_ORIGINS/FRONTEND_ORIGIN.
# - FRONTEND_ORIGINS: optional comma-separated list of allowed origins
# - FRONTEND_ORIGIN: single origin (legacy). If both set, both are used.
# Defaults include localhost:3000 (http) and inferred preview https origin for convenience.
frontend_origin_single = os.getenv("FRONTEND_ORIGIN")
frontend_origins_csv = os.getenv("FRONTEND_ORIGINS")

allow_origins: list[str] = []

# Include legacy single origin if provided
if frontend_origin_single:
    allow_origins.append(frontend_origin_single.strip())

# Include CSV origins if provided
if frontend_origins_csv:
    allow_origins.extend([o.strip() for o in frontend_origins_csv.split(",") if o.strip()])

# If nothing provided, include sensible defaults for local dev and preview environment
if not allow_origins:
    # Local development default
    allow_origins.append("http://localhost:3000")
    # Attempt to infer preview frontend origin based on host
    # If backend runs on https://<host>:3001, frontend likely at https://<host>:3000
    host = os.getenv("HOSTNAME") or ""
    # The platform URL is not always available; we safely add a generic pattern used by the environment
    allow_origins.append("https://vscode-internal-42596-beta.beta01.cloud.kavia.ai:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize shared resources such as the database connection and ensure indexes on notes collection."""
    await connect_to_mongo()
    # Ensure indexes
    db: AsyncIOMotorDatabase
    async for db in get_db():  # use dependency generator to get db instance
        notes: AsyncIOMotorCollection = db.get_collection("notes")
        # Index on updatedAt descending for efficient listing
        await notes.create_index([("updatedAt", -1)], name="idx_updatedAt_desc")
        # Optional index on title for potential searches
        await notes.create_index([("title", 1)], name="idx_title_asc")
        break


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Cleanup shared resources such as the database connection."""
    await close_mongo_connection()


@app.get("/", tags=["health"], summary="Health Check")
def health_check():
    """Return a simple health status to indicate the service is running."""
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.get(
    "/notes",
    response_model=List[NoteOut],
    tags=["notes"],
    summary="List notes",
    description="Retrieve all notes ordered by updatedAt in descending order.",
    responses={
        200: {"description": "List of notes."},
    },
)
async def list_notes(collection: AsyncIOMotorCollection = Depends(get_notes_collection)) -> List[NoteOut]:
    """List notes ordered by updatedAt descending."""
    cursor = collection.find({}, sort=[("updatedAt", -1)])
    notes: List[NoteOut] = []
    async for doc in cursor:
        notes.append(mongo_doc_to_note_out(doc))
    return notes


# PUBLIC_INTERFACE
@app.post(
    "/notes",
    response_model=NoteOut,
    status_code=status.HTTP_201_CREATED,
    tags=["notes"],
    summary="Create a note",
    description="Create a new note. Server will set createdAt and updatedAt timestamps.",
    responses={
        201: {"description": "Note created successfully."},
        422: {"description": "Validation error."},
    },
)
async def create_note(
    payload: NoteIn = Body(..., description="Note data."),
    collection: AsyncIOMotorCollection = Depends(get_notes_collection),
) -> NoteOut:
    """Create a note with server-generated timestamps."""
    doc = note_in_to_mongo_doc(payload)
    result = await collection.insert_one(doc)
    created = await collection.find_one({"_id": result.inserted_id})
    if created is None:
        # Unexpected, but handle gracefully
        raise HTTPException(status_code=500, detail="Failed to retrieve created note")
    return mongo_doc_to_note_out(created)


def _parse_object_id(id_str: str) -> ObjectId:
    """Helper to parse an ObjectId and raise 400 if invalid."""
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail="Invalid note id")
    return ObjectId(id_str)


# PUBLIC_INTERFACE
@app.get(
    "/notes/{id}",
    response_model=NoteOut,
    tags=["notes"],
    summary="Get a note",
    description="Retrieve a single note by its id.",
    responses={
        200: {"description": "Note found."},
        400: {"description": "Invalid id."},
        404: {"description": "Note not found."},
    },
)
async def get_note(
    id: str = Path(..., description="Note id (ObjectId string)"),
    collection: AsyncIOMotorCollection = Depends(get_notes_collection),
) -> NoteOut:
    """Get a single note by id."""
    oid = _parse_object_id(id)
    doc = await collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Note not found")
    return mongo_doc_to_note_out(doc)


# PUBLIC_INTERFACE
@app.patch(
    "/notes/{id}",
    response_model=NoteOut,
    tags=["notes"],
    summary="Update a note (partial)",
    description="Partially update fields of a note. The server sets updatedAt to now.",
    responses={
        200: {"description": "Note updated."},
        400: {"description": "Invalid id."},
        404: {"description": "Note not found."},
    },
)
async def update_note_partial(
    id: str = Path(..., description="Note id (ObjectId string)"),
    payload: NoteUpdate = Body(..., description="Fields to update."),
    collection: AsyncIOMotorCollection = Depends(get_notes_collection),
) -> NoteOut:
    """Partially update a note and set updatedAt to now."""
    oid = _parse_object_id(id)
    existing = await collection.find_one({"_id": oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")
    new_doc = apply_note_update(existing, payload)
    # Do not allow changing _id or createdAt
    update_fields = {k: v for k, v in new_doc.items() if k not in ["_id", "createdAt"]}
    await collection.update_one({"_id": oid}, {"$set": update_fields})
    updated = await collection.find_one({"_id": oid})
    assert updated is not None
    return mongo_doc_to_note_out(updated)


# PUBLIC_INTERFACE
@app.put(
    "/notes/{id}",
    response_model=NoteOut,
    tags=["notes"],
    summary="Update a note (replace)",
    description="Replace mutable fields of a note. The server sets updatedAt to now.",
    responses={
        200: {"description": "Note updated."},
        400: {"description": "Invalid id."},
        404: {"description": "Note not found."},
    },
)
async def update_note_replace(
    id: str = Path(..., description="Note id (ObjectId string)"),
    payload: NoteIn = Body(..., description="Full note payload to replace current values."),
    collection: AsyncIOMotorCollection = Depends(get_notes_collection),
) -> NoteOut:
    """Replace a note's title and content and set updatedAt to now."""
    oid = _parse_object_id(id)
    existing = await collection.find_one({"_id": oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")
    # Keep createdAt, update content/title and updatedAt
    replacement = {
        "title": payload.title,
        "content": payload.content,
        "createdAt": existing.get("createdAt", datetime.utcnow()),
        "updatedAt": datetime.utcnow(),
    }
    await collection.update_one({"_id": oid}, {"$set": replacement})
    updated = await collection.find_one({"_id": oid})
    assert updated is not None
    return mongo_doc_to_note_out(updated)


# PUBLIC_INTERFACE
@app.delete(
    "/notes/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["notes"],
    summary="Delete a note",
    description="Delete a note by its id.",
    responses={
        204: {"description": "Note deleted."},
        400: {"description": "Invalid id."},
        404: {"description": "Note not found."},
    },
)
async def delete_note(
    id: str = Path(..., description="Note id (ObjectId string)"),
    collection: AsyncIOMotorCollection = Depends(get_notes_collection),
) -> JSONResponse:
    """Delete a note by id."""
    oid = _parse_object_id(id)
    result = await collection.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
