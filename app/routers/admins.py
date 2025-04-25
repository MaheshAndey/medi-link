from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import sqlalchemy.orm
from typing import List, Optional
from datetime import datetime, timedelta, date

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

@router.get("/admins/doctors", response_class=HTMLResponse)
def admin_doctors(
    request: Request,
    search: Optional[str] = None,
    specialization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    admin = crud.get_admin_by_user_id(db, current_user.user_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin profile not found")
    
    # Get all specializations for the dropdown filter
    specializations = crud.get_specializations(db)
    
    # Build query for doctors
    query = db.query(models.Doctor).options(
        sqlalchemy.orm.joinedload(models.Doctor.user),
        sqlalchemy.orm.joinedload(models.Doctor.specialization)
    )
    
    # Apply filters if provided
    if search:
        search_term = f"%{search}%"
        query = query.join(models.User).filter(
            sqlalchemy.or_(
                models.Doctor.name.ilike(search_term),
                models.User.email.ilike(search_term)
            )
        )
    
    if specialization_id:
        query = query.filter(models.Doctor.specialization_id == specialization_id)
    
    # Get results
    doctors = query.all()
    
    return templates.TemplateResponse("admin/doctors.html", {
        "request": request,
        "user": current_user,
        "admin": admin,
        "doctors": doctors,
        "specializations": specializations,
        "search": search,
        "specialization_id": specialization_id
    })

@router.get("/admins/doctors/{doctor_id}", response_class=HTMLResponse)
def admin_doctor_detail(
    request: Request,
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    admin = crud.get_admin_by_user_id(db, current_user.user_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin profile not found")
    
    # Get doctor with all relationships
    doctor = db.query(models.Doctor).options(
        sqlalchemy.orm.joinedload(models.Doctor.user),
        sqlalchemy.orm.joinedload(models.Doctor.specialization),
        sqlalchemy.orm.joinedload(models.Doctor.appointments).joinedload(models.Appointment.patient),
        sqlalchemy.orm.joinedload(models.Doctor.health_records).joinedload(models.HealthRecord.patient),
        sqlalchemy.orm.joinedload(models.Doctor.feedbacks).joinedload(models.Feedback.patient),
        sqlalchemy.orm.joinedload(models.Doctor.schedules)
    ).filter(models.Doctor.doctor_id == doctor_id).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Get all specializations for dropdown in edit form
    specializations = crud.get_specializations(db)

    # Get upcoming appointments
    upcoming_appointments = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.appointment_time > datetime.now()
    ).order_by(models.Appointment.appointment_time).limit(5).all()

    # Get past appointments
    past_appointments = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.appointment_time <= datetime.now()
    ).order_by(models.Appointment.appointment_time.desc()).limit(10).all()
    return templates.TemplateResponse("admin/doctor_detail.html", {
        "request": request,
        "user": current_user,
        "admin": admin,
        "doctor": doctor,
        "specializations": specializations,
        "upcoming_appointments": upcoming_appointments,
        "past_appointments": past_appointments,
        "schedule": doctor.schedules,
        "now": datetime.now
    })

@router.get("/admins/patients", response_class=HTMLResponse)
def admin_patients(
    request: Request,
    search: Optional[str] = None,
    gender: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    admin = crud.get_admin_by_user_id(db, current_user.user_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin profile not found")
    
    # Build query for patients
    query = db.query(models.Patient).options(
        sqlalchemy.orm.joinedload(models.Patient.user)
    )
    
    # Apply filters if provided
    if search:
        search_term = f"%{search}%"
        query = query.join(models.User).filter(
            sqlalchemy.or_(
                models.Patient.name.ilike(search_term),
                models.User.email.ilike(search_term)
            )
        )
    
    if gender:
        query = query.filter(models.Patient.gender == gender)
    
    # Get results
    patients = query.all()
    
    return templates.TemplateResponse("admin/patients.html", {
        "request": request,
        "user": current_user,
        "admin": admin,
        "patients": patients,
        "search": search,
        "gender": gender,
        "now": datetime.now
    })

@router.get("/admins/patients/{patient_id}", response_class=HTMLResponse)
def admin_patient_detail(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    admin = crud.get_admin_by_user_id(db, current_user.user_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin profile not found")
    
    # Get patient with all relationships
    patient = db.query(models.Patient).options(
        sqlalchemy.orm.joinedload(models.Patient.user),
        sqlalchemy.orm.joinedload(models.Patient.appointments).joinedload(models.Appointment.doctor),
        sqlalchemy.orm.joinedload(models.Patient.health_records).joinedload(models.HealthRecord.doctor),
        sqlalchemy.orm.joinedload(models.Patient.billings)
    ).filter(models.Patient.patient_id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get appointments
    appointments = db.query(models.Appointment).options(
        sqlalchemy.orm.joinedload(models.Appointment.doctor).joinedload(models.Doctor.specialization)
    ).filter(models.Appointment.patient_id == patient_id).order_by(models.Appointment.appointment_time.desc()).all()
    
    # Get health records
    health_records = db.query(models.HealthRecord).options(
        sqlalchemy.orm.joinedload(models.HealthRecord.doctor).joinedload(models.Doctor.specialization)
    ).filter(models.HealthRecord.patient_id == patient_id).order_by(models.HealthRecord.created_at.desc()).all()
    
    # Get billings
    billings = db.query(models.Billing).options(
        sqlalchemy.orm.joinedload(models.Billing.appointment).joinedload(models.Appointment.doctor)
    ).filter(models.Billing.patient_id == patient_id).order_by(models.Billing.created_at.desc()).all()
    
    return templates.TemplateResponse("admin/patient_detail.html", {
        "request": request,
        "user": current_user,
        "admin": admin,
        "patient": patient,
        "appointments": appointments,
        "health_records": health_records,
        "billings": billings,
        "now": datetime.now
    })

@router.get("/admins/appointments", response_class=HTMLResponse)
def admin_appointments(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    doctor_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role),
    appointment_date: Optional[str] = Form(None),
    appointment_time: Optional[str] = Form(None)
):
    admin = crud.get_admin_by_user_id(db, current_user.user_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin profile not found")
    
    # Get all doctors for dropdown filter
    doctors = crud.get_doctors(db)
    
    # Build query for appointments
    query = db.query(models.Appointment).options(
        sqlalchemy.orm.joinedload(models.Appointment.patient),
        sqlalchemy.orm.joinedload(models.Appointment.doctor).joinedload(models.Doctor.specialization)
    )
    
    # Apply filters if provided
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(func.date(models.Appointment.appointment_time) >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(func.date(models.Appointment.appointment_time) <= to_date)
        except ValueError:
            pass
    
    if doctor_id:
        query = query.filter(models.Appointment.doctor_id == doctor_id)
    
    if status:
        query = query.filter(models.Appointment.status == status)
    
    #Combine date and time into a datetime object
    if appointment_date and appointment_time:
        try:
            appointment_datetime = datetime.strptime(f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date or time format")

    # Get results sorted by appointment time
    appointments = query.order_by(models.Appointment.appointment_time).all()
    
    patients = crud.get_patients(db)

    return templates.TemplateResponse("admin/appointments.html", {
        "request": request,
        "user": current_user,
        "admin": admin,
        "appointments": appointments,
        "doctors": doctors,
        "date_from": date_from,
        "date_to": date_to,
        "doctor_id": doctor_id,
        "status": status,
        "now": datetime.now,
        "patients": patients
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
    
    specializations = crud.get_specializations(db)

    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "user": current_user,
        "admin": admin,
        "users": users,
        "search": search,
        "specializations": specializations
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

@router.post("/api/doctors/{doctor_id}")
async def update_doctor_api(
    doctor_id: int,
    name: str = Form(...),
    specialization_id: Optional[int] = Form(None),
    qualification: Optional[str] = Form(None),
    experience: Optional[int] = Form(None),
    consultation_fee: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Get doctor
    doctor = crud.get_doctor(db, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Update doctor
    doctor_update = schemas.DoctorUpdate(
        name=name,
        specialization_id=specialization_id,
        qualification=qualification,
        experience=experience,
        consultation_fee=consultation_fee
    )
    
    updated_doctor = crud.update_doctor(db, doctor_id, doctor_update)
    if not updated_doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    return RedirectResponse(url=f"/admins/doctors", status_code=303)

@router.post("/api/patients/{patient_id}")
async def update_patient_api(
    patient_id: int,
    name: str = Form(...),
    dob: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Get patient
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Convert dob string to date if provided
    dob_date = None
    if dob:
        try:
            dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Update patient
    patient_update = schemas.PatientUpdate(
        name=name,
        dob=dob_date,
        gender=gender,
        contact=contact,
        address=address
    )
    
    updated_patient = crud.update_patient(db, patient_id, patient_update)
    if not updated_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return RedirectResponse(url=f"/admins/patients", status_code=303)

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

@router.post("/admins/patients/create")
async def create_patient_by_admin(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    dob: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Check if user already exists
    user = crud.get_user_by_email(db, email)
    if user:
        return RedirectResponse(
            url="/admins/patients?error=Email+already+registered",
            status_code=303
        )

    # Create registration data
    from datetime import datetime
    dob_date = None
    if dob:
        try:
            dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
        except ValueError:
            return RedirectResponse(
                url="/admins/patients?error=Invalid+date+format",
                status_code=303
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

    # Redirect to patients list
    return RedirectResponse(url="/admins/patients", status_code=303)

@router.post("/admins/doctors/create")
async def create_doctor_by_admin(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    specialization_id: Optional[int] = Form(None),
    experience: Optional[int] = Form(None),
    contact: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Check if user already exists
    user = crud.get_user_by_email(db, email)
    if user:
        return RedirectResponse(
            url="/admins/doctors?error=Email+already+registered",
            status_code=303
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

    # Redirect to doctors list
    return RedirectResponse(url="/admins/doctors", status_code=303)
