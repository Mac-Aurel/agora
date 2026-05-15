from fastapi import FastAPI

app = FastAPI(title="Agora — Content")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "content"}
