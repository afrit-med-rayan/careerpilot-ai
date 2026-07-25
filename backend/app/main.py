from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.resumes import router as resumes_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing special for now (Alembic handles migrations externally)
    yield
    # Shutdown


def create_app() -> FastAPI:
    app = FastAPI(
        title="CareerPilot AI",
        description="AI-powered resume & job application platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow frontend dev server and production origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(auth_router)
    app.include_router(resumes_router)

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok", "service": "careerpilot-api"}

    return app


app = create_app()
