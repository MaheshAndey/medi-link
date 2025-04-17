from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_active_user, check_patient_role

router = APIRouter(
    prefix="/api/feedback",
    tags=["feedback"]
)

templates = Jinja2Templates(directory="app/templates")

@router.post("", response_model=schemas.FeedbackResponse)
def create_feedback_api(
    feedback: schemas.FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_patient_role)
):
    # Check if patient is authorized
    patient = crud.get_patient_by_user_id(db, current_user.user_id)
    if not patient or feedback.patient_id != patient.patient_id:
        raise HTTPException(status_code=403, detail="Not authorized to submit feedback for this patient")
    
    # Check if appointment exists and belongs to this patient
    appointment = db.query(models.Appointment).filter(
        models.Appointment.appointment_id == feedback.appointment_id,
        models.Appointment.patient_id == patient.patient_id,
        models.Appointment.doctor_id == feedback.doctor_id
    ).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found or does not belong to this patient")
    
    # Check if feedback already exists for this appointment
    existing_feedback = db.query(models.Feedback).filter(
        models.Feedback.appointment_id == feedback.appointment_id
    ).first()
    
    if existing_feedback:
        raise HTTPException(status_code=400, detail="Feedback already submitted for this appointment")
    
    # Create feedback
    feedback_db = crud.create_feedback(db, feedback)
    
    # Create notification for doctor
    doctor = crud.get_doctor(db, feedback.doctor_id)
    if doctor and doctor.user_id:
        notification_data = schemas.NotificationCreate(
            user_id=doctor.user_id,
            title="New Feedback",
            message=f"You have received a {feedback.rating}/5 rating from a patient.",
            is_read=False
        )
        crud.create_notification(db, notification_data)
    
    return feedback_db

@router.get("", response_model=List[schemas.FeedbackResponse])
def read_feedbacks_api(
    doctor_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Filter feedbacks based on user role and parameters
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        
        # Patients can only see their own feedbacks or feedbacks for doctors they've seen
        if doctor_id:
            # Check if patient has had an appointment with this doctor
            appointment = db.query(models.Appointment).filter(
                models.Appointment.patient_id == patient.patient_id,
                models.Appointment.doctor_id == doctor_id
            ).first()
            
            if not appointment:
                raise HTTPException(status_code=403, detail="Not authorized to access feedbacks for this doctor")
            
            feedbacks = db.query(models.Feedback).filter(
                models.Feedback.doctor_id == doctor_id
            ).all()
        else:
            # Get patient's own feedbacks
            feedbacks = crud.get_patient_feedbacks(db, patient.patient_id)
    
    elif current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        
        # Doctors can see feedbacks for themselves
        feedbacks = crud.get_doctor_feedbacks(db, doctor.doctor_id)
    
    elif current_user.role == "admin":
        # Admins can filter or see all
        if doctor_id:
            feedbacks = crud.get_doctor_feedbacks(db, doctor_id)
        elif patient_id:
            feedbacks = crud.get_patient_feedbacks(db, patient_id)
        else:
            feedbacks = db.query(models.Feedback).all()
    
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return feedbacks

@router.get("/{feedback_id}", response_model=schemas.FeedbackResponse)
def read_feedback_api(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Get feedback
    feedback = crud.get_feedback(db, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Check access rights
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient or feedback.patient_id != patient.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this feedback")
    
    elif current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if not doctor or feedback.doctor_id != doctor.doctor_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this feedback")
    
    return feedback

@router.put("/{feedback_id}", response_model=schemas.FeedbackResponse)
def update_feedback_api(
    feedback_id: int,
    feedback: schemas.FeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_patient_role)
):
    # Get feedback
    db_feedback = crud.get_feedback(db, feedback_id)
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Check if patient is authorized
    patient = crud.get_patient_by_user_id(db, current_user.user_id)
    if not patient or db_feedback.patient_id != patient.patient_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this feedback")
    
    # Update feedback
    updated_feedback = crud.update_feedback(db, feedback_id, feedback)
    
    return updated_feedback

@router.delete("/{feedback_id}", response_model=bool)
def delete_feedback_api(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Get feedback
    db_feedback = crud.get_feedback(db, feedback_id)
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Check if user is authorized
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient or db_feedback.patient_id != patient.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this feedback")
    
    elif current_user.role == "admin":
        # Admins can delete any feedback
        pass
    
    else:
        raise HTTPException(status_code=403, detail="Not authorized to delete feedbacks")
    
    # Delete feedback
    success = crud.delete_feedback(db, feedback_id)
    if not success:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return success
