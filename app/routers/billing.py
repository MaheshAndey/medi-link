from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_active_user, check_admin_role

router = APIRouter(
    prefix="/api/billing",
    tags=["billing"]
)

templates = Jinja2Templates(directory="app/templates")

@router.post("", response_model=schemas.BillingResponse)
def create_billing_api(
    billing: schemas.BillingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Check if patient exists
    patient = crud.get_patient(db, billing.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check if appointment exists
    appointment = crud.get_appointment(db, billing.appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Create billing
    billing_db = crud.create_billing(db, billing)
    
    # Create notification for patient
    notification_data = schemas.NotificationCreate(
        user_id=patient.user_id,
        title="New Billing",
        message=f"A new billing of ${billing.amount} has been generated for your appointment on {appointment.appointment_time.strftime('%Y-%m-%d')}.",
        is_read=False
    )
    crud.create_notification(db, notification_data)
    
    return billing_db

@router.get("", response_model=List[schemas.BillingResponse])
def read_billings_api(
    patient_id: Optional[int] = None,
    appointment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Filter billings based on user role and parameters
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        
        # Patients can only see their own billings
        billings = crud.get_patient_billings(db, patient.patient_id)
    
    elif current_user.role == "doctor":
        # Doctors can see billings for patients they've treated
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        
        if patient_id:
            # Check if doctor has treated this patient
            appointment = db.query(models.Appointment).filter(
                models.Appointment.doctor_id == doctor.doctor_id,
                models.Appointment.patient_id == patient_id
            ).first()
            
            if not appointment:
                raise HTTPException(status_code=403, detail="Not authorized to access billings for this patient")
            
            billings = crud.get_patient_billings(db, patient_id)
        
        elif appointment_id:
            # Check if appointment belongs to this doctor
            appointment = db.query(models.Appointment).filter(
                models.Appointment.appointment_id == appointment_id,
                models.Appointment.doctor_id == doctor.doctor_id
            ).first()
            
            if not appointment:
                raise HTTPException(status_code=403, detail="Not authorized to access billings for this appointment")
            
            billings = db.query(models.Billing).filter(
                models.Billing.appointment_id == appointment_id
            ).all()
        
        else:
            # Get all appointments for this doctor
            appointments = crud.get_doctor_appointments(db, doctor.doctor_id)
            appointment_ids = [appointment.appointment_id for appointment in appointments]
            
            # Get billings for these appointments
            billings = db.query(models.Billing).filter(
                models.Billing.appointment_id.in_(appointment_ids)
            ).all()
    
    elif current_user.role == "admin":
        # Admins can filter or see all
        if patient_id:
            billings = crud.get_patient_billings(db, patient_id)
        elif appointment_id:
            billings = db.query(models.Billing).filter(
                models.Billing.appointment_id == appointment_id
            ).all()
        else:
            billings = db.query(models.Billing).all()
    
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return billings

@router.get("/{billing_id}", response_model=schemas.BillingResponse)
def read_billing_api(
    billing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Get billing
    billing = crud.get_billing(db, billing_id)
    if not billing:
        raise HTTPException(status_code=404, detail="Billing not found")
    
    # Check access rights
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient or billing.patient_id != patient.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this billing")
    
    elif current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        
        # Check if the appointment belongs to this doctor
        appointment = db.query(models.Appointment).filter(
            models.Appointment.appointment_id == billing.appointment_id,
            models.Appointment.doctor_id == doctor.doctor_id
        ).first()
        
        if not appointment:
            raise HTTPException(status_code=403, detail="Not authorized to access this billing")
    
    return billing

@router.put("/{billing_id}", response_model=schemas.BillingResponse)
def update_billing_api(
    billing_id: int,
    billing: schemas.BillingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Get billing
    db_billing = crud.get_billing(db, billing_id)
    if not db_billing:
        raise HTTPException(status_code=404, detail="Billing not found")
    
    # Update billing
    updated_billing = crud.update_billing(db, billing_id, billing)
    
    # Create notification for patient if status changed
    if billing.status and billing.status != db_billing.status:
        patient = crud.get_patient(db, db_billing.patient_id)
        if patient and patient.user_id:
            notification_data = schemas.NotificationCreate(
                user_id=patient.user_id,
                title="Billing Status Updated",
                message=f"Your billing status has been updated to {billing.status}.",
                is_read=False
            )
            crud.create_notification(db, notification_data)
    
    return updated_billing

@router.delete("/{billing_id}", response_model=bool)
def delete_billing_api(
    billing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Delete billing
    success = crud.delete_billing(db, billing_id)
    if not success:
        raise HTTPException(status_code=404, detail="Billing not found")
    
    return success
