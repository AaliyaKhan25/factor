"""FastAPI app: routers, startup."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import models  # noqa: F401  (registers every model on Base.metadata)
from .db import Base, engine
from .routers import auth, business, team


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Development convenience. In production, run Alembic migrations instead.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Factor API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(business.router)
app.include_router(team.router)


@app.get("/health")
def health():
    return {"status": "ok"}
