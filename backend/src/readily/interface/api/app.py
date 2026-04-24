"""FastAPI composition root.

Builds the app once, wires routes, and registers CORS for the Next.js dev
origin. All request-scoped wiring lives in `deps.py`. Use the factory form
with uvicorn:

    uvicorn readily.interface.api.app:create_app --factory --reload
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from readily.interface.api.routes import info, policies, questions, results, upload


def create_app() -> FastAPI:
    origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

    app = FastAPI(
        title="Readily API",
        version="0.1.0",
        description=(
            "Read-only view of the Readily claim-comparison pipeline output "
            "(questions, policies, results) plus a PDF passthrough and an "
            "upload stub. The pipeline itself runs offline via the CLI."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins if o.strip()],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(info.router)
    app.include_router(questions.router)
    app.include_router(policies.router)
    app.include_router(results.router)
    app.include_router(upload.router)
    return app
