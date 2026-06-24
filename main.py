from fastapi import FastAPI

app = FastAPI(
    title="ToolUniverse Proxy",
    description="Minimal health check service.",
    version="1.0.0"
)

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "tooluniverse-proxy"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/debug")
def debug():
    return {
        "status": "ok",
        "message": "Render port binding works."
    }
