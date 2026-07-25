# AI Service — FastAPI

import logging
import os
from logging.handlers import TimedRotatingFileHandler

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.routers.learn import router as learn_router
from app.routers.test import router as test_router

# ── File logging setup ──────────────────────────────────────────────────────
_LOG_DIR = "/tmp/logs"
os.makedirs(_LOG_DIR, exist_ok=True)

_handler = TimedRotatingFileHandler(
    filename=os.path.join(_LOG_DIR, "ai-service.log"),
    when="midnight",
    backupCount=30,
    encoding="utf-8",
)
_handler.suffix = "%Y-%m-%d.log"
_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(threadName)s] %(levelname)-5s %(name)s - %(message)s")
)

logging.basicConfig(level=logging.INFO, handlers=[_handler])
# uvicorn loggers
for _name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    _log = logging.getLogger(_name)
    _log.handlers = [_handler]
    _log.propagate = False

app = FastAPI(title="PrepPilot AI Service", version="0.1.0")

app.include_router(learn_router)
app.include_router(test_router)


@app.get("/health")
def health():
    return JSONResponse(content={"status": "ok"})
