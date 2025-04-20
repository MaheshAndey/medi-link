from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_active_user, check_doctor_role, check_doctor_or_admin_role

router = APIRouter(
    prefix="/api/tests",
    tags=["tests"]
)

templates = Jinja2Templates(directory="app/templates")


@router.post("/{test_id}/status")
def update_test_status(
    test_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    # Get test
    db_test = crud.get_test(db, test_id)
    if not db_test:
        raise HTTPException(status_code=404, detail="Test not found")

    # Check if doctor is authorized
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor or db_test.ordered_by != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this test")

    # Update test status
    test_update = schemas.TestUpdate(status=status)
    updated_test = crud.update_test(db, test_id, test_update)

    # Get health record for redirect
    health_record = crud.get_health_record(db, db_test.record_id)

    # Redirect back to health record detail page
    return RedirectResponse(
        url=f"/doctors/health-records/{health_record.record_id}",
        status_code=303
    )

@router.post("", response_model=schemas.TestResponse)
def create_test_api(
    test: schemas.TestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    # Check if health record exists
    health_record = crud.get_health_record(db, test.record_id)
    if not health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Check if doctor is authorized
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor or test.ordered_by != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="Not authorized to order tests for this patient")
    
    # Create test
    test_db = crud.create_test(db, test)
    
    # Create notification for patient
    patient = crud.get_patient(db, health_record.patient_id)
    if patient and patient.user_id:
        notification_data = schemas.NotificationCreate(
            user_id=patient.user_id,
            title="New Test Ordered",
            message=f"Dr. {doctor.name} has ordered a {test.test_name} test for you.",
            is_read=False
        )
        crud.create_notification(db, notification_data)
    
    return test_db

@router.get("", response_model=List[schemas.TestResponse])
def read_tests_api(
    record_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # If record_id is provided, get tests for that record
    if record_id:
        # Check if health record exists
        health_record = crud.get_health_record(db, record_id)
        if not health_record:
            raise HTTPException(status_code=404, detail="Health record not found")
        
        # Check access rights
        if current_user.role == "patient":
            patient = crud.get_patient_by_user_id(db, current_user.user_id)
            if not patient or health_record.patient_id != patient.patient_id:
                raise HTTPException(status_code=403, detail="Not authorized to access tests for this health record")
        
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
                    raise HTTPException(status_code=403, detail="Not authorized to access tests for this health record")
        
        # Get tests
        tests = crud.get_record_tests(db, record_id)
    
    else:
        # Without record_id, limit results based on user role
        if current_user.role == "patient":
            patient = crud.get_patient_by_user_id(db, current_user.user_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Patient profile not found")
            
            # Get all health records for this patient
            health_records = crud.get_patient_health_records(db, patient.patient_id)
            
            # Get tests for each health record
            tests = []
            for record in health_records:
                tests.extend(crud.get_record_tests(db, record.record_id))
        
        elif current_user.role == "doctor":
            doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
            if not doctor:
                raise HTTPException(status_code=404, detail="Doctor profile not found")
            
            # Get tests ordered by this doctor
            tests = db.query(models.Test).filter(
                models.Test.ordered_by == doctor.doctor_id
            ).all()
        
        elif current_user.role == "admin":
            # Admins can see all tests
            tests = db.query(models.Test).all()
        
        else:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return tests

@router.get("/{test_id}", response_model=schemas.TestResponse)
def read_test_api(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Get test
    test = crud.get_test(db, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Get health record to check access rights
    health_record = crud.get_health_record(db, test.record_id)
    if not health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Check access rights
    if current_user.role == "patient":
        patient = crud.get_patient_by_user_id(db, current_user.user_id)
        if not patient or health_record.patient_id != patient.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this test")
    
    elif current_user.role == "doctor":
        doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        
        # Check if this doctor ordered the test, created the record, or has treated this patient
        if test.ordered_by != doctor.doctor_id and health_record.doctor_id != doctor.doctor_id:
            # Check if doctor has treated this patient (has an appointment)
            appointment = db.query(models.Appointment).filter(
                models.Appointment.doctor_id == doctor.doctor_id,
                models.Appointment.patient_id == health_record.patient_id
            ).first()
            
            if not appointment:
                raise HTTPException(status_code=403, detail="Not authorized to access this test")
    
    return test

# @router.put("/{test_id}", response_model=schemas.TestResponse)
# def update_test_api(
#     test_id: int,
#     test: schemas.TestUpdate,
#     db: Session = Depends(get_db),
#     current_user: models.User = Depends(check_doctor_role)
# ):
#     # Get test
#     db_test = crud.get_test(db, test_id)
#     if not db_test:
#         raise HTTPException(status_code=404, detail="Test not found")
    
#     # Check if doctor is authorized (only the doctor who ordered the test can update it)
#     doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
#     if not doctor or db_test.ordered_by != doctor.doctor_id:
#         raise HTTPException(status_code=403, detail="Not authorized to update this test")
    
#     updated_test = crud.update_test(db, test_id, test)

#     health_record = crud.get_health_record(db, db_test.record_id)
#     # Redirect back to health record detail page
#     return RedirectResponse(
#         url=f"/doctors/health-records/{health_record.record_id}",
#         status_code=303
#     )

@router.delete("/{test_id}", response_model=bool)
def delete_test_api(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    # Get test
    db_test = crud.get_test(db, test_id)
    if not db_test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Check if doctor is authorized (only the doctor who ordered the test can delete it)
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor or db_test.ordered_by != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this test")
    
    # Only allow deletion if test is in 'ordered' status
    if db_test.status != "ordered":
        raise HTTPException(status_code=400, detail="Cannot delete test that is already in progress or completed")
    
    # Delete test
    success = crud.delete_test(db, test_id)
    if not success:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return success

@router.post("/{test_id}/update", response_model=schemas.TestResponse)
def update_test_results(
    test_id: int,
    result: str = Form(...),
    report_url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    # Get test
    db_test = crud.get_test(db, test_id)
    if not db_test:
        raise HTTPException(status_code=404, detail="Test not found")

    # Check if doctor is authorized
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor or db_test.ordered_by != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this test")

    # Update test results and report URL
    test_update = schemas.TestUpdate(result=result, report_url=report_url, status="completed")
    updated_test = crud.update_test(db, test_id, test_update)

    # Get health record for redirect
    health_record = crud.get_health_record(db, db_test.record_id)

    # Redirect back to health record detail page
    return RedirectResponse(
        url=f"/doctors/health-records/{health_record.record_id}",
        status_code=303
    )
