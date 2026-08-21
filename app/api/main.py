"""
API layer between the database and any future frontend. Read-only for
now - no endpoints that trigger predictions or writes, those stay as
cron/manual scripts. This just exposes what's already computed.
"""
from fastapi import FastAPI
from app.api.routes import predictions

app = FastAPI(title="CFB Edge API")

app.include_router(predictions.router, prefix="/predictions", tags=["predictions"])


@app.get("/health")
def health_check():
    return {"status": "ok"}