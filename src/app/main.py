from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router

app = FastAPI(title="PropertyFinder Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# run in dev mode with: uvicorn app.main:app --reload
# IMPORTANT: make sure to run the command from the src/ directory, otherwise the relative paths to the data won't work.
