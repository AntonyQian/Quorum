from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config, errors
from app.db import init_db
from app.routers import demo, payments, retailer, shopper


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Quorum API", lifespan=lifespan)
errors.install(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (shopper.router, payments.router, retailer.router, demo.router):
    app.include_router(r, prefix="/api")


@app.get("/health")
def health():
    return {"ok": True}
