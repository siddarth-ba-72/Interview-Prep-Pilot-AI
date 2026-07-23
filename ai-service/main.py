# AI Service — FastAPI

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from routers.learn import router as learn_router

app = FastAPI(title="PrepPilot AI Service", version="0.1.0")

app.include_router(learn_router)


@app.get("/health")
def health():
    return JSONResponse(content={"status": "ok"})
