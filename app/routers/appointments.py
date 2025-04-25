from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app import crud, schemas, models
from app.database import get_db
# Updated dependencies import
from app.dependencies import get_current_active_user, check_patient_role, check_doctor_role, check_admin_role, check_doctor_or_admin_role

router = APIRouter(
    prefix="/api/appointments",
    tags=["appointments"]
)

templates = Jinja2Templates(directory="app/templates")

@router.post("", response_model=schemas.AppointmentResponse)
def create_appointment_api(
    appointment: schemas.AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user) # Consider role check if needed
):
    # Check if patient exists
    patient = crud.get_patient(db, appointment.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check if doctor exists
    doctor = crud.get_doctor(db, appointment.doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Basic check: Ensure the user creating the appointment is the patient themselves or an admin
    # More robust checks might be needed depending on application logic
    if current_user.role == "patient":
        requesting_patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not requesting_patient or requesting_patient.patient_id != appointment.patient_id:
            raise HTTPException(status_code=403, detail="Patients can only book appointments for themselves.")
    elif current_user.role != "admin": # Assuming admins can book for anyone
         raise HTTPException(status_code=403, detail="Unauthorized to book this appointment.")


    # Create appointment
    return crud.create_appointment(db, appointment)

@router.get("", response_model=List[schemas.AppointmentResponse])
def read_appointments_api(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user) # Use base dependency
):
    # Filter appointments based on user role
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient:
            # Return empty list or raise error? Empty list might be safer.
            return []
            # raise HTTPException(status_code=404, detail="Patient profile not found")
        appointments = crud.get_patient_appointments(db, patient.patient_id, skip=skip, limit=limit)

    elif current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if not doctor:
             return []
            # raise HTTPException(status_code=404, detail="Doctor profile not found")
        appointments = crud.get_doctor_appointments(db, doctor.doctor_id, skip=skip, limit=limit)

    elif current_user.role == "admin":
        appointments = crud.get_appointments(db, skip=skip, limit=limit)

    else:
        # Should not happen with proper role setup, but good practice
        raise HTTPException(status_code=403, detail="Not authorized")

    return appointments

@router.get("/{appointment_id}", response_model=schemas.AppointmentResponse)
def read_appointment_api(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user) # Use base dependency
):
    # Get appointment
    appointment = crud.get_appointment(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Check access rights based on role
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        # Ensure patient profile exists and the appointment belongs to this patient
        if not patient or appointment.patient_id != patient.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this appointment")

    elif current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        # Ensure doctor profile exists and the appointment belongs to this doctor
        if not doctor or appointment.doctor_id != doctor.doctor_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this appointment")

    elif current_user.role != "admin": # Admins have access implicitly here
         raise HTTPException(status_code=403, detail="Not authorized")


    return appointment

@router.put("/{appointment_id}", response_model=schemas.AppointmentResponse)
def update_appointment_api(
    appointment_id: int,
    appointment_update: schemas.AppointmentUpdate, # Renamed for clarity
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user) # Use base dependency
):
    # Get appointment
    db_appointment = crud.get_appointment(db, appointment_id)
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Authorization checks
    can_update = False
    if current_user.role == "admin":
        can_update = True
    elif current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if patient and db_appointment.patient_id == patient.patient_id:
            # Patients can only cancel (or maybe update reason if allowed by schema?)
            if appointment_update.status and appointment_update.status != schemas.AppointmentStatus.cancelled:
                 raise HTTPException(status_code=403, detail="Patients can only cancel appointments via this method.")
            # Prevent patients from changing other fields if AppointmentUpdate allows more
            # Create a new update schema containing only allowed fields if necessary
            can_update = True # Allow update if status is 'cancelled' or None (e.g., updating reason)
    elif current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if doctor and db_appointment.doctor_id == doctor.doctor_id:
            # Doctors might update status (e.g., confirmed, completed, no_show)
            can_update = True

    if not can_update:
        raise HTTPException(status_code=403, detail="Not authorized to update this appointment")


    # Perform the update
    updated_appointment = crud.update_appointment(db, appointment_id, appointment_update)
    if not updated_appointment:
         # Should ideally not happen if get_appointment succeeded, but defensive check
        raise HTTPException(status_code=404, detail="Appointment could not be updated.")


    # Create notification for the other party involved in the appointment
    notification_recipient_user_id = None
    notification_title = "Appointment Update"
    notification_message = ""

    if current_user.role == "patient" and updated_appointment.doctor and updated_appointment.doctor.user:
        notification_recipient_user_id = updated_appointment.doctor.user.user_id
        status_text = f"to status: {updated_appointment.status.value}" if updated_appointment.status else "details updated"
        notification_message = f"Your appointment with {updated_appointment.patient.name} on {updated_appointment.appointment_time.strftime('%Y-%m-%d %H:%M')} was updated ({status_text})."
        if updated_appointment.status == schemas.AppointmentStatus.cancelled:
            notification_title = "Appointment Cancelled"
            notification_message = f"Your appointment with {updated_appointment.patient.name} on {updated_appointment.appointment_time.strftime('%Y-%m-%d %H:%M')} has been cancelled by the patient."


    elif current_user.role == "doctor" and updated_appointment.patient and updated_appointment.patient.user:
        notification_recipient_user_id = updated_appointment.patient.user.user_id
        status_text = f"to status: {updated_appointment.status.value}" if updated_appointment.status else "details updated"
        notification_message = f"Your appointment with Dr. {updated_appointment.doctor.name} on {updated_appointment.appointment_time.strftime('%Y-%m-%d %H:%M')} has been updated ({status_text})."

    elif current_user.role == "admin":
         # Notify both patient and doctor if admin makes a change?
         # Notify Patient
        if updated_appointment.patient and updated_appointment.patient.user:
            patient_user_id = updated_appointment.patient.user.user_id
            status_text = f"to status: {updated_appointment.status.value}" if updated_appointment.status else "details updated"
            p_message = f"Your appointment on {updated_appointment.appointment_time.strftime('%Y-%m-%d %H:%M')} was updated by an administrator ({status_text})."
            crud.create_notification(db, schemas.NotificationCreate(user_id=patient_user_id, title="Appointment Update (Admin)", message=p_message, is_read=False))
         # Notify Doctor
        if updated_appointment.doctor and updated_appointment.doctor.user:
            doctor_user_id = updated_appointment.doctor.user.user_id
            status_text = f"to status: {updated_appointment.status.value}" if updated_appointment.status else "details updated"
            d_message = f"Appointment for {updated_appointment.patient.name} on {updated_appointment.appointment_time.strftime('%Y-%m-%d %H:%M')} was updated by an administrator ({status_text})."
            crud.create_notification(db, schemas.NotificationCreate(user_id=doctor_user_id, title="Appointment Update (Admin)", message=d_message, is_read=False))


    # Send notification if recipient identified and not an admin update (handled above)
    if notification_recipient_user_id and current_user.role != "admin":
        notification_data = schemas.NotificationCreate(
            user_id=notification_recipient_user_id,
            title=notification_title,
            message=notification_message,
            is_read=False
        )
        crud.create_notification(db, notification_data)

    return updated_appointment


# <<< Added POST endpoint for cancellation from HTML form >>>
@router.post("/{appointment_id}/cancel", response_class=RedirectResponse)
def cancel_appointment_from_form(
    appointment_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_patient_role) # Ensure only patients use this
):
    if status != "cancelled":
        # Although the form sends 'cancelled', check just in case
        raise HTTPException(status_code=400, detail="Invalid status for cancellation")

    # Get appointment
    db_appointment = crud.get_appointment(db, appointment_id)
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Verify the appointment belongs to the current patient
    patient = crud.get_patient_by_user_id(db, current_user.user_id)
    if not patient or db_appointment.patient_id != patient.patient_id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this appointment")

    # Check if appointment is already cancelled or completed
    if db_appointment.status in [schemas.AppointmentStatus.cancelled, schemas.AppointmentStatus.completed]:
         # Optionally redirect with a message? Or just redirect silently.
         # For now, redirect silently. The UI should ideally prevent cancelling already cancelled/completed ones.
         return RedirectResponse(url="/patients/appointments", status_code=status.HTTP_303_SEE_OTHER)


    # Prepare update data
    appointment_update = schemas.AppointmentUpdate(status=schemas.AppointmentStatus.cancelled)

    # Perform the update
    updated_appointment = crud.update_appointment(db, appointment_id, appointment_update)
    if not updated_appointment:
        raise HTTPException(status_code=500, detail="Failed to cancel appointment") # Or 404 if update failed due to not found

    # Create notification for the doctor
    if updated_appointment.doctor and updated_appointment.doctor.user:
        notification_data = schemas.NotificationCreate(
            user_id=updated_appointment.doctor.user.user_id,
            title="Appointment Cancelled",
            message=f"Appointment with {patient.name} on {updated_appointment.appointment_time.strftime('%Y-%m-%d %H:%M')} has been cancelled by the patient.",
            is_read=False
        )
        crud.create_notification(db, notification_data)

    # Redirect back to the appointments page
    return RedirectResponse(url="/patients/appointments", status_code=303)


@router.delete("/{appointment_id}", response_model=bool)
def delete_appointment_api(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role) # Ensure only admins can delete
):
    # Check if appointment exists before attempting delete
    db_appointment = crud.get_appointment(db, appointment_id)
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Only admins can hard delete appointments via API
    success = crud.delete_appointment(db, appointment_id)
    if not success:
         # This might happen in a race condition, or if delete logic fails
        raise HTTPException(status_code=500, detail="Failed to delete appointment")

    return True # Return True on successful deletion

@router.get("/doctor/{doctor_id}/available", response_model=List[dict])
def get_available_slots_api(
    doctor_id: int,
    date: str, # Keep as string for input validation
    db: Session = Depends(get_db),
    # No specific role check needed? Anyone logged in can check availability?
    # current_user: models.User = Depends(get_current_active_user)
):
    try:
        # Validate and parse the date string
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD")

    # Optional: Check if doctor exists
    doctor = crud.get_doctor(db, doctor_id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")


    # Get available slots using the CRUD function
    try:
        slots = crud.get_available_slots(db, doctor_id, target_date)
    except Exception as e:
         # Log the error e
         print(f"Error fetching available slots: {e}") # Basic logging
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve available slots.")


    # Format slots for the JSON response
    result = []
    for start_time, end_time in slots:
        result.append({
            "start": start_time.strftime("%H:%M"),
            "end": end_time.strftime("%H:%M")
        })
    
    return result
