"""
Runner to start the FastAPI app with uvicorn, binding to 0.0.0.0 and port from env.

Usage:
    python -m src.api
"""
import os
import uvicorn

def main() -> None:
    # PUBLIC_INTERFACE
    """
    Entrypoint to run uvicorn server for the Notes Backend API.
    Binds to 0.0.0.0 to be accessible from preview environment.
    """
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "3001"))
    uvicorn.run("src.api.main:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main()
