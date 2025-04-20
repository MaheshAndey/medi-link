from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi import HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_active_user, check_doctor_role, check_doctor_or_admin_role

router = APIRouter(
    prefix="/api/prescriptions",
    tags=["prescriptions"]
)

templates = Jinja2Templates(directory="app/templates")

@router.post("", response_model=schemas.PrescriptionResponse)
def create_prescription_api(
    prescription: schemas.PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    # Check if health record exists
    health_record = crud.get_health_record(db, prescription.record_id)
    if not health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Check if doctor is authorized
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor or health_record.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="Not authorized to create prescription for this health record")
    
    # Create prescription
    prescription_db = crud.create_prescription(db, prescription)
    
    # Create notification for patient
    patient = crud.get_patient(db, health_record.patient_id)
    if patient and patient.user_id:
        notification_data = schemas.NotificationCreate(
            user_id=patient.user_id,
            title="New Prescription",
            message=f"Dr. {doctor.name} has prescribed {prescription.medication_name} for you.",
            is_read=False
        )
        crud.create_notification(db, notification_data)
    
    return prescription_db

@router.post("/{prescription_id}")
def delete_prescription_api(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    # Get prescription
    prescription = crud.get_prescription(db, prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Get health record to check authorization
    health_record = crud.get_health_record(db, prescription.record_id)
    if not health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Check if doctor is authorized
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor or health_record.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this prescription")
    
    # Delete prescription
    success = crud.delete_prescription(db, prescription_id)
    if not success:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Redirect to health record page
    return RedirectResponse(url=f"/doctors/health-records/{health_record.record_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.get("", response_model=List[schemas.PrescriptionResponse])
def read_prescriptions_api(
    record_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # If record_id is provided, get prescriptions for that record
    if record_id:
        # Check if health record exists
        health_record = crud.get_health_record(db, record_id)
        if not health_record:
            raise HTTPException(status_code=404, detail="Health record not found")
        
        # Check access rights
        if current_user.role == "patient":
            patient = crud.get_patient_by_user_id(db, current_user.user_id)
            if not patient or health_record.patient_id != patient.patient_id:
                raise HTTPException(status_code=403, detail="Not authorized to access prescriptions for this health record")
        
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
                    raise HTTPException(status_code=403, detail="Not authorized to access prescriptions for this health record")
        
        # Get prescriptions
        prescriptions = crud.get_record_prescriptions(db, record_id)
    
    else:
        # Without record_id, limit results based on user role
        if current_user.role == "patient":
            patient = crud.get_patient_by_user_id(db, current_user.user_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Patient profile not found")
            
            # Get all health records for this patient
            health_records = crud.get_patient_health_records(db, patient.patient_id)
            
            # Get prescriptions for each health record
            prescriptions = []
            for record in health_records:
                prescriptions.extend(crud.get_record_prescriptions(db, record.record_id))
        
        elif current_user.role == "doctor":
            doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
            if not doctor:
                raise HTTPException(status_code=404, detail="Doctor profile not found")
            
            # Get all health records created by this doctor
            health_records = db.query(models.HealthRecord).filter(
                models.HealthRecord.doctor_id == doctor.doctor_id
            ).all()
            
            # Get prescriptions for each health record
            prescriptions = []
            for record in health_records:
                prescriptions.extend(crud.get_record_prescriptions(db, record.record_id))
        
        elif current_user.role == "admin":
            # Admins can see all prescriptions
            prescriptions = db.query(models.Prescription).all()
        
        else:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return prescriptions

@router.get("/{prescription_id}", response_model=schemas.PrescriptionResponse)
def read_prescription_api(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Get prescription
    prescription = crud.get_prescription(db, prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Get health record to check access rights
    health_record = crud.get_health_record(db, prescription.record_id)
    if not health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Check access rights
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient or health_record.patient_id != patient.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this prescription")
    
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
                raise HTTPException(status_code=403, detail="Not authorized to access this prescription")
    
    return prescription

@router.put("/{prescription_id}", response_model=schemas.PrescriptionResponse)
def update_prescription_api(
    prescription_id: int,
    prescription: schemas.PrescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    # Get prescription
    db_prescription = crud.get_prescription(db, prescription_id)
    if not db_prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Get health record to check access rights
    health_record = crud.get_health_record(db, db_prescription.record_id)
    if not health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Check if doctor is authorized (only the doctor who created the health record can update prescriptions)
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor or health_record.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this prescription")
    
    # Update prescription
    updated_prescription = crud.update_prescription(db, prescription_id, prescription)
    
    # Create notification for patient
    patient = crud.get_patient(db, health_record.patient_id)
    if patient and patient.user_id:
        notification_data = schemas.NotificationCreate(
            user_id=patient.user_id,
            title="Prescription Updated",
            message=f"Dr. {doctor.name} has updated your prescription for {updated_prescription.medication_name}.",
            is_read=False
        )
        crud.create_notification(db, notification_data)
    
    return updated_prescription

@router.delete("/{prescription_id}", response_model=bool)
def delete_prescription_api(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    # Get prescription
    db_prescription = crud.get_prescription(db, prescription_id)
    if not db_prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Get health record to check access rights
    health_record = crud.get_health_record(db, db_prescription.record_id)
    if not health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Check if doctor is authorized (only the doctor who created the health record can delete prescriptions)
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor or health_record.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this prescription")
    
    # Delete prescription
    success = crud.delete_prescription(db, prescription_id)
    if not success:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    return success
