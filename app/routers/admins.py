from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_active_user, check_admin_role
from app.security import get_password_hash

router = APIRouter(
    tags=["admins"]
)

templates = Jinja2Templates(directory="app/templates")

@router.get("/admins/dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    admin = crud.get_admin_by_user_id(db, current_user.user_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin profile not found")
    
    # Get counts for dashboard
    user_count = db.query(models.User).count()
    patient_count = db.query(models.Patient).count()
    doctor_count = db.query(models.Doctor).count()
    appointment_count = db.query(models.Appointment).count()
    
    # Get recent appointments
    recent_appointments = db.query(models.Appointment).order_by(
        models.Appointment.created_at.desc()
    ).limit(5).all()
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": current_user,
        "admin": admin,
        "user_count": user_count,
        "patient_count": patient_count,
        "doctor_count": doctor_count,
        "appointment_count": appointment_count,
        "recent_appointments": recent_appointments
    })

@router.get("/admins/users", response_class=HTMLResponse)
def admin_users(
    request: Request,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    admin = crud.get_admin_by_user_id(db, current_user.user_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin profile not found")
    
    # Get users with search filter if provided
    query = db.query(models.User)
    if search:
        query = query.filter(models.User.email.ilike(f"%{search}%"))
    
    users = query.all()
    
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "user": current_user,
        "admin": admin,
        "users": users,
        "search": search
    })

@router.post("/admins/users/create")
def create_user(
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Check if user already exists
    existing_user = crud.get_user_by_email(db, email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = crud.create_user(db, schemas.UserCreate(
        email=email,
        password=password,
        role=role
    ))
    
    # Create profile based on role
    if role == "patient":
        crud.create_patient(db, schemas.PatientCreate(
            user_id=user.user_id,
            name=name
        ))
    elif role == "doctor":
        crud.create_doctor(db, schemas.DoctorCreate(
            user_id=user.user_id,
            name=name
        ))
    elif role == "admin":
        crud.create_admin(db, schemas.AdminCreate(
            user_id=user.user_id,
            name=name
        ))
    
    return RedirectResponse(url="/admins/users", status_code=303)

@router.post("/admins/users/{user_id}/update")
def update_user_status(
    user_id: int,
    is_active: bool = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Update user active status
    user_update = schemas.UserUpdate(is_active=is_active)
    updated_user = crud.update_user(db, user_id, user_update)
    
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return RedirectResponse(url="/admins/users", status_code=303)

@router.post("/admins/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Get user
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update password
    hashed_password = get_password_hash(new_password)
    user.password_hash = hashed_password
    db.commit()
    
    return RedirectResponse(url="/admins/users", status_code=303)

@router.get("/admins/specializations", response_class=HTMLResponse)
def admin_specializations(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    admin = crud.get_admin_by_user_id(db, current_user.user_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin profile not found")
    
    # Get all specializations
    specializations = crud.get_specializations(db)
    
    return templates.TemplateResponse("admin/specializations.html", {
        "request": request,
        "user": current_user,
        "admin": admin,
        "specializations": specializations
    })

@router.post("/admins/specializations/create")
def create_specialization(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Create specialization
    specialization_data = schemas.SpecializationCreate(
        name=name,
        description=description
    )
    
    specialization = crud.create_specialization(db, specialization_data)
    
    return RedirectResponse(url="/admins/specializations", status_code=303)

@router.post("/admins/specializations/{specialization_id}/update")
def update_specialization(
    specialization_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Update specialization
    specialization_update = schemas.SpecializationUpdate(
        name=name,
        description=description
    )
    
    updated_specialization = crud.update_specialization(db, specialization_id, specialization_update)
    
    if not updated_specialization:
        raise HTTPException(status_code=404, detail="Specialization not found")
    
    return RedirectResponse(url="/admins/specializations", status_code=303)

@router.post("/admins/specializations/{specialization_id}/delete")
def delete_specialization(
    specialization_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Check if specialization is in use
    doctors = db.query(models.Doctor).filter(
        models.Doctor.specialization_id == specialization_id
    ).count()
    
    if doctors > 0:
        raise HTTPException(status_code=400, detail="Cannot delete specialization that is assigned to doctors")
    
    # Delete specialization
    success = crud.delete_specialization(db, specialization_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Specialization not found")
    
    return RedirectResponse(url="/admins/specializations", status_code=303)

# API Endpoints
@router.post("/api/admins", response_model=schemas.AdminResponse)
def create_admin_api(
    admin: schemas.AdminCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    return crud.create_admin(db, admin)

@router.get("/api/admins", response_model=List[schemas.AdminResponse])
def read_admins_api(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    admins = crud.get_admins(db, skip=skip, limit=limit)
    return admins

@router.get("/api/admins/{admin_id}", response_model=schemas.AdminResponse)
def read_admin_api(
    admin_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    db_admin = crud.get_admin(db, admin_id=admin_id)
    if db_admin is None:
        raise HTTPException(status_code=404, detail="Admin not found")
    return db_admin

@router.put("/api/admins/{admin_id}", response_model=schemas.AdminResponse)
def update_admin_api(
    admin_id: int,
    admin: schemas.AdminUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    db_admin = crud.update_admin(db, admin_id=admin_id, admin_update=admin)
    if db_admin is None:
        raise HTTPException(status_code=404, detail="Admin not found")
    return db_admin

@router.delete("/api/admins/{admin_id}", response_model=bool)
def delete_admin_api(
    admin_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    success = crud.delete_admin(db, admin_id=admin_id)
    if not success:
        raise HTTPException(status_code=404, detail="Admin not found")
    return success

@router.post("/api/specializations", response_model=schemas.SpecializationResponse)
def create_specialization_api(
    specialization: schemas.SpecializationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    return crud.create_specialization(db, specialization)

@router.get("/api/specializations", response_model=List[schemas.SpecializationResponse])
def read_specializations_api(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    specializations = crud.get_specializations(db, skip=skip, limit=limit)
    return specializations

@router.get("/api/specializations/{specialization_id}", response_model=schemas.SpecializationResponse)
def read_specialization_api(
    specialization_id: int,
    db: Session = Depends(get_db)
):
    db_specialization = crud.get_specialization(db, specialization_id=specialization_id)
    if db_specialization is None:
        raise HTTPException(status_code=404, detail="Specialization not found")
    return db_specialization
