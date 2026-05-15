from fastapi import FastAPI

app = FastAPI(title="Agora — Discovery")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "discovery"}
