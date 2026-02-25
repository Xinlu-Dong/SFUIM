from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app.core.persistence import restore_all_sessions
from app.core.storage import session_store


app = FastAPI(title="SFUIM Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本地联调先放开，部署时再收紧
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

restore_all_sessions(session_store)

