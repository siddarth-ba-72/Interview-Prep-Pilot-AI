# AI Service — FastAPI

import logging
import sys

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.routers.learn import router as learn_router
from app.routers.test import router as test_router

# Console logging setup
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(threadName)s] %(levelname)-5s %(name)s - %(message)s")
)

logging.basicConfig(level=logging.INFO, handlers=[_handler], force=True)
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
