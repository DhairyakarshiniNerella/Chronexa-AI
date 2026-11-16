
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models
from models import Base
from database import engine

from app.routes.tasks import router as task_router
from app.routes.auth import router as auth_router
from app.routes.notes import router as notes_router
from app.routes.schedules import router as schedule_router
from app.routes.reminders import router as reminder_router
from app.routes.ai import router as ai_router

from app.scheduler import start_scheduler, stop_scheduler


# Application startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):

    # Create database tables during startup
    Base.metadata.create_all(bind=engine)

    # Start background reminder scheduler
    start_scheduler()

    try:
        yield
    finally:
        stop_scheduler()


# Create FastAPI application
app = FastAPI(
    title="Chronexa AI",
    description="AI-powered personal productivity assistant",
    version="1.0.0",
    lifespan=lifespan
)


# CORS configuration
allowed_origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:5501",
    "http://localhost:5501",
]

# Add deployed frontend URL from environment
frontend_url = os.getenv("FRONTEND_URL", "").strip()

if frontend_url:
    allowed_origins.extend(
        origin.strip()
        for origin in frontend_url.split(",")
        if origin.strip()
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routers
app.include_router(task_router)
app.include_router(auth_router)
app.include_router(notes_router)
app.include_router(schedule_router)
app.include_router(reminder_router)
app.include_router(ai_router)


# Home API
@app.get("/")
def home():
    return {
        "message": "Welcome to Chronexa AI!",
        "status": "Backend is running successfully"
    }
