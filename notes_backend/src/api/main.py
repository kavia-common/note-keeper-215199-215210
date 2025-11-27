from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.db import connect_to_mongo, close_mongo_connection

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust per environment as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize shared resources such as the database connection."""
    await connect_to_mongo()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Cleanup shared resources such as the database connection."""
    await close_mongo_connection()


@app.get("/", tags=["health"], summary="Health Check")
def health_check():
    """Return a simple health status to indicate the service is running."""
    return {"message": "Healthy"}
