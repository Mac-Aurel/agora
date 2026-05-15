from fastapi import FastAPI

app = FastAPI(title="Agora — Boards")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "boards"}
