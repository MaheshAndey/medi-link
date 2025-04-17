from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_active_user, check_doctor_role, check_doctor_or_admin_role

router = APIRouter(
    prefix="/api/health-records",
    tags=["health_records"]
)

templates = Jinja2Templates(directory="app/templates")

@router.post("", response_model=schemas.HealthRecordResponse)
def create_health_record_api(
    health_record: schemas.HealthRecordCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    # Check if doctor is authorized
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor or health_record.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="Not authorized to create health record for this doctor")
    
    # Check if patient exists
    patient = crud.get_patient(db, health_record.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Create health record
    health_record_db = crud.create_health_record(db, health_record)
    
    # Create notification for patient
    notification_data = schemas.NotificationCreate(
        user_id=patient.user_id,
        title="New Health Record",
        message=f"Dr. {doctor.name} has created a new health record for you.",
        is_read=False
    )
    crud.create_notification(db, notification_data)
    
    return health_record_db

@router.get("", response_model=List[schemas.HealthRecordResponse])
def read_health_records_api(
    patient_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Filter health records based on user role and parameters
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        
        # Patients can only see their own records
        health_records = crud.get_patient_health_records(db, patient.patient_id, skip=skip, limit=limit)
    
    elif current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        
        # If patient_id is provided, check if the doctor has seen this patient
        if patient_id:
            # Check if doctor has treated this patient (has an appointment)
            appointment = db.query(models.Appointment).filter(
                models.Appointment.doctor_id == doctor.doctor_id,
                models.Appointment.patient_id == patient_id
            ).first()
            
            if not appointment:
                raise HTTPException(status_code=403, detail="Not authorized to access this patient's records")
            
            health_records = crud.get_patient_health_records(db, patient_id, skip=skip, limit=limit)
        else:
            # Get all health records created by this doctor
            health_records = db.query(models.HealthRecord).filter(
                models.HealthRecord.doctor_id == doctor.doctor_id
            ).offset(skip).limit(limit).all()
    
    elif current_user.role == "admin":
        if patient_id:
            health_records = crud.get_patient_health_records(db, patient_id, skip=skip, limit=limit)
        else:
            # Admins can see all health records
            health_records = db.query(models.HealthRecord).offset(skip).limit(limit).all()
    
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return health_records

@router.get("/{record_id}", response_model=schemas.HealthRecordResponse)
def read_health_record_api(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Get health record
    health_record = crud.get_health_record(db, record_id)
    if not health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Check access rights
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient or health_record.patient_id != patient.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this health record")
    
    elif current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        
        # Check if this doctor created the record or has treated this patient
        if health_record.doctor_id != doctor.doctor_id:
            # Check if doctor has treated this patient (has an appointment)
            appointment = db.query(models.Appointment).filter(
                models.Appointment.doctor_id == doctor.doctor_id,
                models.Appointment.patient_id == health_record.patient_id
            ).first()
            
            if not appointment:
                raise HTTPException(status_code=403, detail="Not authorized to access this health record")
    
    return health_record

@router.put("/{record_id}", response_model=schemas.HealthRecordResponse)
def update_health_record_api(
    record_id: int,
    health_record: schemas.HealthRecordUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    # Get health record
    db_health_record = crud.get_health_record(db, record_id)
    if not db_health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Check if doctor is authorized (only the doctor who created the record can update it)
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor or db_health_record.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this health record")
    
    # Update health record
    updated_health_record = crud.update_health_record(db, record_id, health_record)
    
    # Create notification for patient
    patient = crud.get_patient(db, db_health_record.patient_id)
    if patient and patient.user_id:
        notification_data = schemas.NotificationCreate(
            user_id=patient.user_id,
            title="Health Record Updated",
            message=f"Dr. {doctor.name} has updated your health record.",
            is_read=False
        )
        crud.create_notification(db, notification_data)
    
    return updated_health_record

@router.delete("/{record_id}", response_model=bool)
def delete_health_record_api(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_or_admin_role)
):
    # Get health record
    db_health_record = crud.get_health_record(db, record_id)
    if not db_health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Check if user is authorized
    if current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if not doctor or db_health_record.doctor_id != doctor.doctor_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this health record")
    
    # Delete health record
    success = crud.delete_health_record(db, record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    return success
