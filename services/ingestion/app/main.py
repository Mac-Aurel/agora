from fastapi import FastAPI

app = FastAPI(title="Agora — Ingestion")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "ingestion"}
