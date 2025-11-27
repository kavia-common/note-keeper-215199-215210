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

Preview environment setup:
- The frontend origin must be explicitly whitelisted:
  FRONTEND_ORIGINS="https://vscode-internal-42596-beta.beta01.cloud.kavia.ai:3000,http://localhost:3000"
- Ensure the backend is accessed via HTTPS on port 3001 by the frontend:
  Set the frontend API base to https://vscode-internal-42596-beta.beta01.cloud.kavia.ai:3001
- The backend binds to 0.0.0.0 so it is reachable externally by the preview host.

MongoDB connectivity:
- This service uses lazy MongoDB connection with resilience. If Mongo is unreachable at startup, the app still boots and returns HTTP 503 with an actionable message for DB-dependent routes.
- To use the provided preview Mongo endpoint, set:
  MONGODB_URL="mongodb://appuser:dbuser123@localhost:5000/?authSource=admin"
  MONGODB_DB="notes_app"
- If your DB is exposed under a different host/port, update MONGODB_URL accordingly.

Troubleshooting "Failed to fetch" from frontend:
- Confirm CORS includes the exact preview origin (see FRONTEND_ORIGINS).
- Confirm the frontend uses HTTPS API base URL (avoid mixed content).
- If DB is down, GET /notes will return 503 with a message instead of crashing the backend.

Generate OpenAPI spec (writes interfaces/openapi.json):
    python -m src.api.generate_openapi
