from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_active_user, check_patient_role, check_doctor_role, check_admin_role

router = APIRouter(
    prefix="/api/appointments",
    tags=["appointments"]
)

templates = Jinja2Templates(directory="app/templates")

@router.post("", response_model=schemas.AppointmentResponse)
def create_appointment_api(
    appointment: schemas.AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Check if patient exists
    patient = crud.get_patient(db, appointment.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check if doctor exists
    doctor = crud.get_doctor(db, appointment.doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Create appointment
    return crud.create_appointment(db, appointment)

@router.get("", response_model=List[schemas.AppointmentResponse])
def read_appointments_api(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Filter appointments based on user role
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        appointments = crud.get_patient_appointments(db, patient.patient_id, skip=skip, limit=limit)
    
    elif current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        appointments = crud.get_doctor_appointments(db, doctor.doctor_id, skip=skip, limit=limit)
    
    elif current_user.role == "admin":
        appointments = crud.get_appointments(db, skip=skip, limit=limit)
    
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return appointments

@router.get("/{appointment_id}", response_model=schemas.AppointmentResponse)
def read_appointment_api(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Get appointment
    appointment = crud.get_appointment(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check access rights
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient or appointment.patient_id != patient.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this appointment")
    
    elif current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if not doctor or appointment.doctor_id != doctor.doctor_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this appointment")
    
    return appointment

@router.put("/{appointment_id}", response_model=schemas.AppointmentResponse)
def update_appointment_api(
    appointment_id: int,
    appointment: schemas.AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Get appointment
    db_appointment = crud.get_appointment(db, appointment_id)
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check access rights
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient or db_appointment.patient_id != patient.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this appointment")
        
        # Patients can only update reason or cancel
        if appointment.status and appointment.status != "cancelled":
            raise HTTPException(status_code=403, detail="Patients can only cancel appointments")
    
    elif current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if not doctor or db_appointment.doctor_id != doctor.doctor_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this appointment")
    
    # Update appointment
    updated_appointment = crud.update_appointment(db, appointment_id, appointment)
    
    # Create notification for the other party
    if current_user.role == "patient" and updated_appointment.doctor and updated_appointment.doctor.user_id:
        notification_data = schemas.NotificationCreate(
            user_id=updated_appointment.doctor.user_id,
            title="Appointment Update",
            message=f"Appointment on {updated_appointment.appointment_time.strftime('%Y-%m-%d %H:%M')} has been updated.",
            is_read=False
        )
        crud.create_notification(db, notification_data)
    
    elif current_user.role == "doctor" and updated_appointment.patient and updated_appointment.patient.user_id:
        notification_data = schemas.NotificationCreate(
            user_id=updated_appointment.patient.user_id,
            title="Appointment Update",
            message=f"Your appointment with Dr. {updated_appointment.doctor.name} on {updated_appointment.appointment_time.strftime('%Y-%m-%d %H:%M')} has been updated to status: {updated_appointment.status}.",
            is_read=False
        )
        crud.create_notification(db, notification_data)
    
    return updated_appointment

@router.delete("/{appointment_id}", response_model=bool)
def delete_appointment_api(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    # Only admins can delete appointments
    success = crud.delete_appointment(db, appointment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return success

@router.get("/doctor/{doctor_id}/available", response_model=List[dict])
def get_available_slots_api(
    doctor_id: int,
    date: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get available slots
    slots = crud.get_available_slots(db, doctor_id, target_date)
    
    # Format slots for response
    result = []
    for start_time, end_time in slots:
        result.append({
            "start": start_time.strftime("%H:%M"),
            "end": end_time.strftime("%H:%M")
        })
    
    return result
