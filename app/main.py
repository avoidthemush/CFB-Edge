"""
Main API entry point - the actual FastAPI app that Railway's web
service runs (per Procfile: uvicorn app.main:app).

CORS enabled (Aug 2026) - the frontend (Next.js, running on a different
domain/port than this API) needs explicit permission to fetch data from
here, or the browser blocks the request by default.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import predictions

app = FastAPI(title="CFB Edge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # personal, single-user project - open is fine for now
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(predictions.router, prefix="/predictions", tags=["predictions"])


@app.get("/")
def health_check():
    return {"status": "ok", "service": "cfb-betting-model"}