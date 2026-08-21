"""
Main API entry point - the actual FastAPI app that Railway's web
service runs (per Procfile: uvicorn app.main:app). Consolidates what
was a placeholder health-check-only file with the real prediction API
built out under app/api/routes/.
"""
from fastapi import FastAPI
from app.api.routes import predictions

app = FastAPI(title="CFB Edge API")

app.include_router(predictions.router, prefix="/predictions", tags=["predictions"])


@app.get("/")
def health_check():
    return {"status": "ok", "service": "cfb-betting-model"}