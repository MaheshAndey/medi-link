from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_active_user, check_patient_role, check_doctor_or_admin_role, check_admin_role

router = APIRouter(
    tags=["patients"]
)

templates = Jinja2Templates(directory="app/templates")

# Routes requiring patient role
@router.get("/patients/dashboard", response_class=HTMLResponse)
def patient_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_patient_role)
):
    patient = crud.get_patient_by_user_id(db, current_user.user_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    
    # Get upcoming appointments
    appointments = crud.get_patient_appointments(db, patient.patient_id)
    
    # Get recent health records
    health_records = crud.get_patient_health_records(db, patient.patient_id)
    
    # Get outstanding bills
    billings = crud.get_patient_billings(db, patient.patient_id)
    
    return templates.TemplateResponse("patient/dashboard.html", {
        "request": request,
        "user": current_user,
        "patient": patient,
        "appointments": appointments,
        "health_records": health_records,
        "billings": billings
    })

@router.get("/patients/appointments", response_class=HTMLResponse)
def patient_appointments(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_patient_role)
):
    patient = crud.get_patient_by_user_id(db, current_user.user_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    
    # Get all appointments
    appointments = crud.get_patient_appointments(db, patient.patient_id)
    
    # Get all doctors for booking new appointments
    doctors = crud.get_doctors(db)
    
    return templates.TemplateResponse("patient/appointments.html", {
        "request": request,
        "user": current_user,
        "patient": patient,
        "appointments": appointments,
        "doctors": doctors
    })

@router.post("/patients/appointments/book")
def book_appointment(
    doctor_id: int = Form(...),
    appointment_date: str = Form(...),
    appointment_time: str = Form(...),
    reason: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_patient_role)
):
    patient = crud.get_patient_by_user_id(db, current_user.user_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    
    # Combine date and time into a datetime object
    from datetime import datetime
    try:
        appointment_datetime = datetime.strptime(f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date or time format")
    
    # Create appointment
    appointment_data = schemas.AppointmentCreate(
        patient_id=patient.patient_id,
        doctor_id=doctor_id,
        appointment_time=appointment_datetime,
        reason=reason,
        status=schemas.AppointmentStatus.scheduled
    )
    
    appointment = crud.create_appointment(db, appointment_data)
    
    # Create notification for doctor
    doctor = crud.get_doctor(db, doctor_id)
    if doctor and doctor.user_id:
        notification_data = schemas.NotificationCreate(
            user_id=doctor.user_id,
            title="New Appointment",
            message=f"New appointment scheduled with {patient.name} on {appointment_datetime.strftime('%Y-%m-%d %H:%M')}",
            is_read=False
        )
        crud.create_notification(db, notification_data)
    
    return RedirectResponse(url="/patients/appointments", status_code=303)

@router.get("/patients/health-records", response_class=HTMLResponse)
def patient_health_records(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_patient_role)
):
    patient = crud.get_patient_by_user_id(db, current_user.user_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    
    # Get all health records
    health_records = crud.get_patient_health_records(db, patient.patient_id)
    
    return templates.TemplateResponse("patient/health_records.html", {
        "request": request,
        "user": current_user,
        "patient": patient,
        "health_records": health_records
    })

@router.get("/patients/prescriptions", response_class=HTMLResponse)
def patient_prescriptions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_patient_role)
):
    patient = crud.get_patient_by_user_id(db, current_user.user_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    
    # Get all health records
    health_records = crud.get_patient_health_records(db, patient.patient_id)
    
    # Get prescriptions for each health record
    prescriptions_by_record = {}
    for record in health_records:
        prescriptions_by_record[record.record_id] = crud.get_record_prescriptions(db, record.record_id)
    
    return templates.TemplateResponse("patient/prescriptions.html", {
        "request": request,
        "user": current_user,
        "patient": patient,
        "health_records": health_records,
        "prescriptions_by_record": prescriptions_by_record
    })

@router.get("/patients/tests", response_class=HTMLResponse)
def patient_tests(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_patient_role)
):
    patient = crud.get_patient_by_user_id(db, current_user.user_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    
    # Get all health records
    health_records = crud.get_patient_health_records(db, patient.patient_id)
    
    # Get tests for each health record
    tests_by_record = {}
    for record in health_records:
        tests_by_record[record.record_id] = crud.get_record_tests(db, record.record_id)
    
    return templates.TemplateResponse("patient/tests.html", {
        "request": request,
        "user": current_user,
        "patient": patient,
        "health_records": health_records,
        "tests_by_record": tests_by_record
    })

@router.get("/patients/billing", response_class=HTMLResponse)
def patient_billing(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_patient_role)
):
    patient = crud.get_patient_by_user_id(db, current_user.user_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    
    # Get all billings
    billings = crud.get_patient_billings(db, patient.patient_id)
    
    return templates.TemplateResponse("patient/billing.html", {
        "request": request,
        "user": current_user,
        "patient": patient,
        "billings": billings
    })

@router.get("/patients/insurance", response_class=HTMLResponse)
def patient_insurance(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_patient_role)
):
    patient = crud.get_patient_by_user_id(db, current_user.user_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    
    # Get all insurances
    insurances = crud.get_patient_insurances(db, patient.patient_id)
    
    return templates.TemplateResponse("patient/insurance.html", {
        "request": request,
        "user": current_user,
        "patient": patient,
        "insurances": insurances
    })

@router.post("/patients/insurance/add")
def add_insurance(
    provider_name: str = Form(...),
    policy_number: str = Form(...),
    coverage_details: Optional[str] = Form(None),
    valid_until: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_patient_role)
):
    patient = crud.get_patient_by_user_id(db, current_user.user_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    
    # Parse valid_until date
    from datetime import datetime
    valid_until_date = None
    if valid_until:
        try:
            valid_until_date = datetime.strptime(valid_until, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Create insurance
    insurance_data = schemas.InsuranceCreate(
        patient_id=patient.patient_id,
        provider_name=provider_name,
        policy_number=policy_number,
        coverage_details=coverage_details,
        valid_until=valid_until_date
    )
    
    insurance = crud.create_insurance(db, insurance_data)
    
    return RedirectResponse(url="/patients/insurance", status_code=303)

# Routes requiring doctor or admin role
@router.get("/admin/patients", response_class=HTMLResponse)
def admin_patients_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_or_admin_role)
):
    patients = crud.get_patients(db)
    
    return templates.TemplateResponse("admin/patients.html", {
        "request": request,
        "user": current_user,
        "patients": patients
    })

@router.get("/admin/patients/{patient_id}", response_class=HTMLResponse)
def admin_patient_detail(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_or_admin_role)
):
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get health records
    health_records = crud.get_patient_health_records(db, patient_id)
    
    # Get appointments
    appointments = crud.get_patient_appointments(db, patient_id)
    
    # Get billings
    billings = crud.get_patient_billings(db, patient_id)
    
    return templates.TemplateResponse("admin/patient_detail.html", {
        "request": request,
        "user": current_user,
        "patient": patient,
        "health_records": health_records,
        "appointments": appointments,
        "billings": billings
    })

# API Endpoints for CRUD operations
@router.post("/api/patients", response_model=schemas.PatientResponse)
def create_patient_api(
    patient: schemas.PatientCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    return crud.create_patient(db, patient)

@router.get("/api/patients", response_model=List[schemas.PatientResponse])
def read_patients_api(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_or_admin_role)
):
    patients = crud.get_patients(db, skip=skip, limit=limit)
    return patients

@router.get("/api/patients/{patient_id}", response_model=schemas.PatientResponse)
def read_patient_api(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_or_admin_role)
):
    db_patient = crud.get_patient(db, patient_id=patient_id)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient

@router.put("/api/patients/{patient_id}", response_model=schemas.PatientResponse)
def update_patient_api(
    patient_id: int,
    patient: schemas.PatientUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_or_admin_role)
):
    db_patient = crud.update_patient(db, patient_id=patient_id, patient_update=patient)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient

@router.delete("/api/patients/{patient_id}", response_model=bool)
def delete_patient_api(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    success = crud.delete_patient(db, patient_id=patient_id)
    if not success:
        raise HTTPException(status_code=404, detail="Patient not found")
    return success
