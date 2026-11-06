
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

from app.scheduler import start_scheduler, stop_scheduler


# Start and stop background scheduler
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


# Create FastAPI application
app = FastAPI(
    title="Chronexa AI",
    description="AI-powered personal productivity assistant",
    version="1.0.0",
    lifespan=lifespan
)


# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5501",
        "http://localhost:5501"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create database tables
Base.metadata.create_all(bind=engine)


# Connect API routers
app.include_router(task_router)
app.include_router(auth_router)
app.include_router(notes_router)
app.include_router(schedule_router)
app.include_router(reminder_router)


# Home API
@app.get("/")
def home():
    return {
        "message": "Welcome to Chronexa AI!",
        "status": "Backend is running successfully"
    }
