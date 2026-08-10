from fastapi import FastAPI

app = FastAPI(title="CFB Betting Model")


@app.get("/")
def health_check():
    return {"status": "ok", "service": "cfb-betting-model"}