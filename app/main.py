from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.connection import Base, engine
from app.db import models  # noqa: F401 (registers tables)
from app.api import auth, progress


app = FastAPI(title="Eduway Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(progress.router)


@app.get("/health")
def health():
    return {"status": "ok"}
