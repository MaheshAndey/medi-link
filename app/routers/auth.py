from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional

from app import crud, schemas
from app.database import get_db
from app.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.dependencies import get_current_user

router = APIRouter(tags=["authentication"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = crud.authenticate_user(db, email, password)
    if not user:
        return RedirectResponse(url="/login?error=Invalid+email+or+password", status_code=303)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Redirect based on role
    if user.role == "patient":
        redirect_url = "/patients/dashboard"
    elif user.role == "doctor":
        redirect_url = "/doctors/dashboard"
    elif user.role == "admin":
        redirect_url = "/admins/dashboard"
    else:
        redirect_url = "/"
    # Create redirect response and SET THE COOKIE
    redirect_response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    redirect_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,  # ! Important: Protects against XSS
        max_age=int(access_token_expires.total_seconds()), # Cookie expiry in seconds
        expires=int(access_token_expires.total_seconds()), # For older browsers
        samesite="lax", # Recommended for security (lax or strict)
        # secure=True, # ! Uncomment this in PRODUCTION if served over HTTPS
    )
    return redirect_response

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return RedirectResponse(url="/login", status_code=303)

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: Optional[str] = None):
    specializations = crud.get_specializations(db)
    return templates.TemplateResponse("register.html", {"request": request, "error": error, "specializations": specializations})

@router.post("/register/patient")
async def register_patient(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    dob: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    # Check if user already exists
    user = crud.get_user_by_email(db, email)
    specializations = crud.get_specializations(db)
    if user:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request,
              "error": "Email already registered",
              "specializations": specializations }
        )
    
    # Create registration data
    from datetime import datetime, date
    dob_date = None
    if dob:
        try:
            dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
        except ValueError:
            return templates.TemplateResponse(
                "register.html", 
                {"request": request, "error": "Invalid date format", "specializations": specializations }
            )
    
    registration_data = schemas.PatientRegistration(
        email=email,
        password=password,
        name=name,
        dob=dob_date,
        gender=gender,
        contact=contact,
        address=address
    )
    
    # Register patient
    patient = crud.register_patient(db, registration_data)
    
    # Redirect to login
    return RedirectResponse(url="/login", status_code=303)

@router.post("/register/doctor")
async def register_doctor(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    specialization_id: Optional[int] = Form(None),
    experience: Optional[int] = Form(None),
    contact: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    # Check if user already exists
    user = crud.get_user_by_email(db, email)
    specializations = crud.get_specializations(db)
    if user:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, 
             "error": "Email already registered", 
             "specializations":specializations}
        )
    
    # Create registration data
    registration_data = schemas.DoctorRegistration(
        email=email,
        password=password,
        name=name,
        specialization_id=specialization_id,
        experience=experience,
        contact=contact
    )
    
    # Register doctor
    doctor = crud.register_doctor(db, registration_data)
    
    # Redirect to login
    return RedirectResponse(url="/login", status_code=303)
