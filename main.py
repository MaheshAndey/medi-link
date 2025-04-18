import os
import logging
from fastapi import FastAPI, Request, Depends, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

from app.database import engine, Base
from app.routers import (
    auth, users, patients, doctors, admins, appointments, 
    health_records, prescriptions, tests, billing, 
    feedback, insurance
)
from app.dependencies import get_current_user
from app.init_db import init_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize database (creates tables and default admin)
logger.info("Initializing database...")
init_db()

app = FastAPI(title="MediLink Healthcare Management System")

# Create middleware for handling session expiration
class SessionExpirationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # If response is 401 Unauthorized and not an API route, redirect to login with expired=true
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            path = request.url.path
            # Skip API routes (typically starting with /api)
            if not path.startswith("/api/") and not path == "/login":
                return RedirectResponse(url="/login?expired=true", status_code=303)
        
        return response

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session expiration middleware
app.add_middleware(SessionExpirationMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(patients.router)
app.include_router(doctors.router)
app.include_router(admins.router)
app.include_router(appointments.router)
app.include_router(health_records.router)
app.include_router(prescriptions.router)
app.include_router(tests.router)
app.include_router(billing.router)
app.include_router(feedback.router)
app.include_router(insurance.router)

@app.get("/")
async def root(request: Request, current_user=Depends(get_current_user)):
    if current_user:
        if current_user.role == "patient":
            return RedirectResponse(url="/patients/dashboard")
        elif current_user.role == "doctor":
            return RedirectResponse(url="/doctors/dashboard")
        elif current_user.role == "admin":
            return RedirectResponse(url="/admins/dashboard")
    return RedirectResponse(url="/login", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
