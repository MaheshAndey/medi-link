import os
from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

from app.database import engine, Base
from app.routers import (
    auth, users, patients, doctors, admins, appointments, 
    health_records, prescriptions, tests, billing, 
    feedback, insurance
)
from app.dependencies import get_current_user

# Load environment variables
load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MediLink Healthcare Management System")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return templates.TemplateResponse("login.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
