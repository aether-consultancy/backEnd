from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dbmanager.connection import Base, engine

from parentmanager import router as parentmanager_router
from kidsmanager import router as kidsmanager_router
from securitymanager import router as securitymanager_router
from sessionmanager import router as sessionmanager_router
from confirmationmanager import router as confirmationmanager_router
from frontendmanager.eduParent import router as fe_eduparent_router
from frontendmanager.eduWay import router as fe_eduway_router


app = FastAPI(title="Eduway Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(parentmanager_router.router)
app.include_router(kidsmanager_router.router)
app.include_router(securitymanager_router.router)
app.include_router(sessionmanager_router.router)
app.include_router(confirmationmanager_router.router)
app.include_router(fe_eduparent_router.router)
app.include_router(fe_eduway_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
