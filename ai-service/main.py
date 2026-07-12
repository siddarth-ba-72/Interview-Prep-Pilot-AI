# AI Service — FastAPI

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="PrepPilot AI Service", version="0.1.0")


@app.get("/health")
def health():
    return JSONResponse(content={"status": "ok"})
