from fastapi import FastAPI

app = FastAPI(title="Agora — Auth")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "auth"}
