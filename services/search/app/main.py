from fastapi import FastAPI

app = FastAPI(title="Agora — Search")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "search"}
