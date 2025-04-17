from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_active_user, check_patient_role, check_admin_role

router = APIRouter(
    prefix="/api/insurance",
    tags=["insurance"]
)

templates = Jinja2Templates(directory="app/templates")

@router.post("", response_model=schemas.InsuranceResponse)
def create_insurance_api(
    insurance: schemas.InsuranceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Check authorization
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient or insurance.patient_id != patient.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized to create insurance for this patient")
    
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to create insurance records")
    
    # Create insurance
    insurance_db = crud.create_insurance(db, insurance)
    
    return insurance_db

@router.get("", response_model=List[schemas.InsuranceResponse])
def read_insurances_api(
    patient_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Filter insurances based on user role and parameters
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        
        # Patients can only see their own insurance
        insurances = crud.get_patient_insurances(db, patient.patient_id)
    
    elif current_user.role == "doctor":
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
                raise HTTPException(status_code=403, detail="Not authorized to access insurance for this patient")
            
            insurances = crud.get_patient_insurances(db, patient_id)
        else:
            raise HTTPException(status_code=400, detail="Patient ID is required")
    
    elif current_user.role == "admin":
        # Admins can filter or see all
        if patient_id:
            insurances = crud.get_patient_insurances(db, patient_id)
        else:
            insurances = db.query(models.Insurance).all()
    
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return insurances

@router.get("/{insurance_id}", response_model=schemas.InsuranceResponse)
def read_insurance_api(
    insurance_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Get insurance
    insurance = crud.get_insurance(db, insurance_id)
    if not insurance:
        raise HTTPException(status_code=404, detail="Insurance not found")
    
    # Check access rights
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient or insurance.patient_id != patient.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this insurance")
    
    elif current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        
        # Check if doctor has treated this patient
        appointment = db.query(models.Appointment).filter(
            models.Appointment.doctor_id == doctor.doctor_id,
            models.Appointment.patient_id == insurance.patient_id
        ).first()
        
        if not appointment:
            raise HTTPException(status_code=403, detail="Not authorized to access insurance for this patient")
    
    return insurance

@router.put("/{insurance_id}", response_model=schemas.InsuranceResponse)
def update_insurance_api(
    insurance_id: int,
    insurance: schemas.InsuranceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Get insurance
    db_insurance = crud.get_insurance(db, insurance_id)
    if not db_insurance:
        raise HTTPException(status_code=404, detail="Insurance not found")
    
    # Check authorization
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient or db_insurance.patient_id != patient.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this insurance")
    
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update insurance records")
    
    # Update insurance
    updated_insurance = crud.update_insurance(db, insurance_id, insurance)
    
    return updated_insurance

@router.delete("/{insurance_id}", response_model=bool)
def delete_insurance_api(
    insurance_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Get insurance
    db_insurance = crud.get_insurance(db, insurance_id)
    if not db_insurance:
        raise HTTPException(status_code=404, detail="Insurance not found")
    
    # Check authorization
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient or db_insurance.patient_id != patient.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this insurance")
    
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete insurance records")
    
    # Delete insurance
    success = crud.delete_insurance(db, insurance_id)
    if not success:
        raise HTTPException(status_code=404, detail="Insurance not found")
    
    return success
