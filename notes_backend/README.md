# Notes Backend

This FastAPI service provides CRUD operations for notes stored in MongoDB.

Development tips:
- Environment:
  - MONGODB_URL: Mongo connection string
  - MONGODB_DB: Database name
  - FRONTEND_ORIGIN: CORS allowed origin (default http://localhost:3000)

Generate OpenAPI spec (writes interfaces/openapi.json):
    python -m src.api.generate_openapi
