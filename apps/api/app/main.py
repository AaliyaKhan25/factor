"""FastAPI app: routers, startup."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (registers every model on Base.metadata)
from .config import settings
from .db import Base, engine
from .routers import auth, business, catalog, channels, customers, dashboard, inbox, orders, team, voice
from .routers import couriers, inventory, payments, sheets, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Development convenience. In production, run Alembic migrations instead.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Factor API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(business.router)
app.include_router(team.router)
app.include_router(catalog.router)
app.include_router(orders.router)
app.include_router(inbox.router)
app.include_router(channels.router)
app.include_router(dashboard.router)
app.include_router(customers.router)
app.include_router(voice.router)
app.include_router(inventory.router)
app.include_router(sheets.router)
app.include_router(webhooks.router)
app.include_router(couriers.router)
app.include_router(payments.router)


@app.get("/health")
def health():
    return {"status": "ok"}
