# AI Service — FastAPI

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.logging_config import setup_structured_logging
from app.error_handlers import register_error_handlers
from app.middleware import UserContextMiddleware
from app.routers.interview import router as interview_router
from app.routers.learn import router as learn_router
from app.routers.test import router as test_router

# Setup structured JSON logging
setup_structured_logging()

app = FastAPI(title="PrepPilot AI Service", version="0.1.0")

# Register middleware for user context extraction
app.add_middleware(UserContextMiddleware)

# Register global error handlers
register_error_handlers(app)

# Include routers
app.include_router(interview_router)
app.include_router(learn_router)
app.include_router(test_router)


@app.get("/health")
def health():
    return JSONResponse(content={"status": "ok"})
