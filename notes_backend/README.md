# Notes Backend

This FastAPI service provides CRUD operations for notes stored in MongoDB.

Development tips:
- Environment:
  - MONGODB_URL: Mongo connection string
  - MONGODB_DB: Database name
  - FRONTEND_ORIGIN: CORS allowed origin (single value; legacy)
  - FRONTEND_ORIGINS: Comma-separated list of allowed origins for CORS (e.g., "http://localhost:3000,https://vscode-internal-42596-beta.beta01.cloud.kavia.ai:3000")
    If neither is set, the service allows http://localhost:3000 and the preview https origin by default.
    Ensure the frontend uses HTTPS API base to avoid mixed-content when the site is served over HTTPS.

Generate OpenAPI spec (writes interfaces/openapi.json):
    python -m src.api.generate_openapi
