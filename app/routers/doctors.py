from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from sqlalchemy.sql.functions import now

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_active_user, check_doctor_role, check_admin_role

import calendar

router = APIRouter(
    tags=["doctors"]
)

templates = Jinja2Templates(directory="app/templates")

# Routes requiring doctor role
@router.get("/doctors/dashboard", response_class=HTMLResponse)
def doctor_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # Appointments
    appointments = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor.doctor_id,
        models.Appointment.appointment_time >= today_start,
        models.Appointment.appointment_time <= today_end
    ).all()

    # Pending Appointments
    pending_appointments = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor.doctor_id,
        models.Appointment.status == "scheduled"
    ).all()

    # Recent Health Records
    recent_records = db.query(models.HealthRecord).filter(
        models.HealthRecord.doctor_id == doctor.doctor_id
    ).order_by(models.HealthRecord.created_at.desc()).limit(5).all()

    # ✅ Use the correct CRUD function to get the doctor's schedule for today
    today_day_name = calendar.day_name[today.weekday()].lower()  # Get today's day (e.g., "monday")
    today_schedule = crud.get_doctor_schedule_for_today(db, doctor_id=doctor.doctor_id, day=today_day_name)

    return templates.TemplateResponse("doctor/dashboard.html", {
        "request": request,
        "user": current_user,
        "doctor": doctor,
        "today_appointments": appointments,
        "pending_appointments": pending_appointments,
        "recent_records": recent_records,
        "today_schedule": today_schedule  # Pass the schedule data to the template
    })



@router.get("/doctors/appointments", response_class=HTMLResponse)
def doctor_appointments(
    request: Request,
    date: Optional[str] = None,
    pending_date_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    # Get appointments for specific date or today
    today = datetime.now().date()
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else today
        if target_date < today:
            target_date = today  # Prevent selection of past dates
    except ValueError:
        target_date = today
    
    target_start = datetime.combine(target_date, datetime.min.time())
    target_end = datetime.combine(target_date, datetime.max.time())
    
    appointments = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor.doctor_id,
        models.Appointment.appointment_time >= target_start,
        models.Appointment.appointment_time <= target_end
    ).all()

    pending_appointments = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor.doctor_id,
        models.Appointment.status == "scheduled",
    )

    if pending_date_filter:
        pending_date = datetime.strptime(pending_date_filter, "%Y-%m-%d").date()
        pending_start_date = datetime.combine(pending_date, datetime.min.time())
        pending_end_date = datetime.combine(pending_date, datetime.max.time())
        pending_appointments = pending_appointments.filter(
            models.Appointment.appointment_time >= pending_start_date,
            models.Appointment.appointment_time <= pending_end_date
        )
    pending_appointments = pending_appointments.all()
    
    # Get schedule for this day
    day_of_week = target_date.strftime("%A").lower()
    schedules = db.query(models.DoctorSchedule).filter(
        models.DoctorSchedule.doctor_id == doctor.doctor_id,
        models.DoctorSchedule.day == day_of_week
    ).all()
    
    return templates.TemplateResponse("doctor/appointments.html", {
        "request": request,
        "user": current_user,
        "doctor": doctor,
        "appointments": appointments,
        "pending_appointments": pending_appointments,
        "schedules": schedules,
        "selected_date": target_date.strftime("%Y-%m-%d"),
        "day_of_week": day_of_week,
        "today": today.strftime("%Y-%m-%d"),
        "today_date": today
    })

@router.post("/api/health-records/{record_id}")
def update_health_record(
    record_id: int,
    symptoms: Optional[str] = Form(None),
    diagnosis: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    # Verify the health record exists and belongs to this doctor
    health_record = db.query(models.HealthRecord).filter(
        models.HealthRecord.record_id == record_id,
        models.HealthRecord.doctor_id == doctor.doctor_id
    ).first()
    
    if not health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Update health record
    health_record_update = schemas.HealthRecordUpdate(
        symptoms=symptoms,
        diagnosis=diagnosis,
        notes=notes
    )
    
    updated_record = crud.update_health_record(db, record_id, health_record_update)
    
    return RedirectResponse(url=f"/doctors/health-records/{record_id}", status_code=303)

@router.post("/doctors/appointments/{appointment_id}/update")
def update_appointment_status(
    appointment_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    # Verify the appointment belongs to this doctor
    appointment = db.query(models.Appointment).filter(
        models.Appointment.appointment_id == appointment_id,
        models.Appointment.doctor_id == doctor.doctor_id
    ).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Update status
    try:
        appointment_status = schemas.AppointmentStatus(status)
        appointment_update = schemas.AppointmentUpdate(status=appointment_status)
        updated_appointment = crud.update_appointment(db, appointment_id, appointment_update)
        
        # Create notification for patient
        notification_data = schemas.NotificationCreate(
            user_id=appointment.patient.user_id,
            title="Appointment Update",
            message=f"Your appointment on {appointment.appointment_time.strftime('%Y-%m-%d %H:%M')} has been updated to {status}",
            is_read=False
        )
        crud.create_notification(db, notification_data)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid appointment status")
    
    return RedirectResponse(url="/doctors/appointments", status_code=303)

@router.get("/doctors/patients", response_class=HTMLResponse)
def doctor_patients(
    request: Request,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    # Get patients who have had appointments with this doctor
    query = db.query(models.Patient).join(
        models.Appointment, models.Patient.patient_id == models.Appointment.patient_id
    ).filter(
        models.Appointment.doctor_id == doctor.doctor_id
    ).distinct()
    
    # Apply search filter if provided
    if search:
        query = query.filter(models.Patient.name.ilike(f"%{search}%"))
    
    patients = query.all()
    
    return templates.TemplateResponse("doctor/patients.html", {
        "request": request,
        "user": current_user,
        "doctor": doctor,
        "patients": patients,
        "search": search,
        "now": datetime.utcnow
    })

@router.get("/doctors/patients/{patient_id}", response_class=HTMLResponse)
def doctor_patient_detail(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get health records for this patient created by this doctor
    health_records = db.query(models.HealthRecord).filter(
        models.HealthRecord.patient_id == patient_id,
        models.HealthRecord.doctor_id == doctor.doctor_id
    ).all()
    
    # Get appointments
    appointments = db.query(models.Appointment).filter(
        models.Appointment.patient_id == patient_id,
        models.Appointment.doctor_id == doctor.doctor_id
    ).all()
    
    return templates.TemplateResponse("doctor/patient_detail.html", {
        "request": request,
        "user": current_user,
        "doctor": doctor,
        "patient": patient,
        "health_records": health_records,
        "appointments": appointments,
        "now": datetime.utcnow
    })

@router.get("/doctors/health-records/create", response_class=HTMLResponse)
def create_health_record_form(
    request: Request,
    patient_id: int,
    appointment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    appointment = None
    if appointment_id:
        appointment = crud.get_appointment(db, appointment_id)
    
    return templates.TemplateResponse("doctor/create_health_record.html", {
        "request": request,
        "user": current_user,
        "doctor": doctor,
        "patient": patient,
        "appointment": appointment,
        "now": datetime.utcnow
    })

@router.post("/doctors/health-records/create")
async def create_health_record(
    request: Request,
    patient_id: int = Form(...),
    appointment_id: Optional[int] = Form(None),
    symptoms: Optional[str] = Form(None),
    diagnosis: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    # Create health record
    health_record_data = schemas.HealthRecordCreate(
        patient_id=patient_id,
        doctor_id=doctor.doctor_id,
        appointment_id=appointment_id,
        symptoms=symptoms,
        diagnosis=diagnosis,
        notes=notes
    )
    
    health_record = crud.create_health_record(db, health_record_data)
    
    # Get form data for prescriptions
    form_data = await request.form()
    
    # Process multiple prescriptions
    prescription_indices = set()
    
    # First collect all valid prescription indices
    for key in form_data.keys():
        if key.startswith('prescriptions[') and key.endswith('][medication_name]'):
            try:
                index = int(key[14:-18])  # Extract index from prescriptions[X][medication_name]
                prescription_indices.add(index)
            except ValueError:
                continue
    
    # Process each valid prescription index
    for index in sorted(prescription_indices):
        medication_name = form_data.get(f'prescriptions[{index}][medication_name]')
        if medication_name and medication_name.strip():  # Only create prescription if medication name is provided and not empty
            prescription = schemas.PrescriptionCreate(
                record_id=health_record.record_id,
                medication_name=medication_name.strip(),
                dosage=form_data.get(f'prescriptions[{index}][dosage]', '').strip(),
                duration=form_data.get(f'prescriptions[{index}][duration]', '').strip(),
                instructions=form_data.get(f'prescriptions[{index}][instructions]', '').strip()
            )
            crud.create_prescription(db, prescription)
    
    # Update appointment status if provided
    if appointment_id:
        appointment_update = schemas.AppointmentUpdate(status=schemas.AppointmentStatus.completed)
        crud.update_appointment(db, appointment_id, appointment_update)
    
    # Create notification for patient
    patient = crud.get_patient(db, patient_id)
    if patient and patient.user_id:
        notification_data = schemas.NotificationCreate(
            user_id=patient.user_id,
            title="New Health Record",
            message=f"Dr. {doctor.name} has created a new health record with prescription for you.",
            is_read=False
        )
        crud.create_notification(db, notification_data)
    
    return RedirectResponse(url=f"/doctors/health-records/{health_record.record_id}", status_code=303)

@router.get("/doctors/health-records/{record_id}", response_class=HTMLResponse)
def view_health_record(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    health_record = crud.get_health_record(db, record_id)
    if not health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Get prescriptions
    prescriptions = crud.get_record_prescriptions(db, record_id)
    
    # Get tests
    tests = crud.get_record_tests(db, record_id)
    
    return templates.TemplateResponse("doctor/health_record_detail.html", {
        "request": request,
        "user": current_user,
        "doctor": doctor,
        "health_record": health_record,
        "prescriptions": prescriptions,
        "tests": tests,
        "now": datetime.utcnow
    })

@router.post("/doctors/prescriptions/create")
def create_prescription(
    record_id: int = Form(...),
    medication_name: str = Form(...),
    dosage: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    duration: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    # Verify the health record exists and belongs to this doctor
    health_record = db.query(models.HealthRecord).filter(
        models.HealthRecord.record_id == record_id,
        models.HealthRecord.doctor_id == doctor.doctor_id
    ).first()
    
    if not health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Create prescription
    prescription_data = schemas.PrescriptionCreate(
        record_id=record_id,
        medication_name=medication_name,
        dosage=dosage,
        instructions=instructions,
        duration=duration
    )
    
    prescription = crud.create_prescription(db, prescription_data)
    
    # Create notification for patient
    if health_record.patient and health_record.patient.user_id:
        notification_data = schemas.NotificationCreate(
            user_id=health_record.patient.user_id,
            title="New Prescription",
            message=f"Dr. {doctor.name} has prescribed {medication_name} for you.",
            is_read=False
        )
        crud.create_notification(db, notification_data)
    
    return RedirectResponse(url=f"/doctors/health-records/{record_id}", status_code=303)

@router.post("/doctors/tests/create")
def create_test(
    record_id: int = Form(...),
    test_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    # Verify the health record exists and belongs to this doctor
    health_record = db.query(models.HealthRecord).filter(
        models.HealthRecord.record_id == record_id,
        models.HealthRecord.doctor_id == doctor.doctor_id
    ).first()
    
    if not health_record:
        raise HTTPException(status_code=404, detail="Health record not found")
    
    # Create test
    test_data = schemas.TestCreate(
        record_id=record_id,
        test_name=test_name,
        status=schemas.TestStatus.ordered,
        ordered_by=doctor.doctor_id
    )
    
    test = crud.create_test(db, test_data)
    
    # Create notification for patient
    if health_record.patient and health_record.patient.user_id:
        notification_data = schemas.NotificationCreate(
            user_id=health_record.patient.user_id,
            title="New Test Ordered",
            message=f"Dr. {doctor.name} has ordered a {test_name} test for you.",
            is_read=False
        )
        crud.create_notification(db, notification_data)
    
    return RedirectResponse(url=f"/doctors/health-records/{record_id}", status_code=303)

@router.get("/doctors/schedule", response_class=HTMLResponse)
def doctor_schedule(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    # Get doctor's schedule
    schedules = crud.get_doctor_schedules(db, doctor.doctor_id)
    
    # Group schedules by day
    schedule_by_day = {}
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day in days:
        schedule_by_day[day] = [s for s in schedules if s.day.lower() == day]
    
    return templates.TemplateResponse("doctor/schedule.html", {
        "request": request,
        "user": current_user,
        "doctor": doctor,
        "schedule_by_day": schedule_by_day,
        "days": days
    })

@router.post("/doctors/schedule/create")
def create_schedule(
    request: Request,
    day: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    is_available: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    if not doctor:
        return templates.TemplateResponse("doctor/schedule.html", {
            "request": request,
            "error": "Doctor profile not found",
            "schedules": [],
            "days": days,
            "user": current_user
        })

    from datetime import datetime
    try:
        start = datetime.strptime(start_time, "%H:%M").time()
        end = datetime.strptime(end_time, "%H:%M").time()

        if start >= end:
            raise ValueError("Start time must be before end time")

    except ValueError as e:
        return templates.TemplateResponse("doctor/schedule.html", {
            "request": request,
            "error": str(e),
            "schedules": crud.get_doctor_schedules(db, doctor.doctor_id),
            "days": days,
            "user": current_user
        })

    # Save the schedule
    schedule_data = schemas.DoctorScheduleCreate(
        doctor_id=doctor.doctor_id,
        day=day.lower(),
        start_time=start,
        end_time=end,
        is_available=is_available
    )
    crud.create_schedule(db, schedule_data)

    return RedirectResponse(url="/doctors/schedule", status_code=303)

@router.post("/doctors/schedule/{schedule_id}/edit")
def edit_schedule(
    schedule_id: int,
    day: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    is_available: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    # Verify schedule belongs to this doctor
    schedule = db.query(models.DoctorSchedule).filter(
        models.DoctorSchedule.schedule_id == schedule_id,
        models.DoctorSchedule.doctor_id == doctor.doctor_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    try:
        start = datetime.strptime(start_time, "%H:%M").time()
        end = datetime.strptime(end_time, "%H:%M").time()
        
        if start >= end:
            raise ValueError("Start time must be before end time")
        
        # Update schedule
        schedule_update = schemas.DoctorScheduleUpdate(
            day=day.lower(),
            start_time=start,
            end_time=end,
            is_available=is_available
        )
        crud.update_schedule(db, schedule_id, schedule_update)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return RedirectResponse(url="/doctors/schedule", status_code=303)

@router.post("/doctors/schedule/{schedule_id}/delete")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    
    # Verify schedule belongs to this doctor
    schedule = db.query(models.DoctorSchedule).filter(
        models.DoctorSchedule.schedule_id == schedule_id,
        models.DoctorSchedule.doctor_id == doctor.doctor_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Delete schedule
    success = crud.delete_schedule(db, schedule_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete schedule")
    
    return RedirectResponse(url="/doctors/schedule", status_code=303)

# Routes requiring admin role
@router.get("/admin/doctors", response_class=HTMLResponse)
def admin_doctors_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    doctors = crud.get_doctors(db)
    specializations = crud.get_specializations(db)
    
    return templates.TemplateResponse("admin/doctors.html", {
        "request": request,
        "user": current_user,
        "doctors": doctors,
        "specializations": specializations
    })

# API Endpoints
@router.post("/api/doctors", response_model=schemas.DoctorResponse)
def create_doctor_api(
    doctor: schemas.DoctorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    return crud.create_doctor(db, doctor)

@router.get("/api/doctors", response_model=List[schemas.DoctorResponse])
def read_doctors_api(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    doctors = crud.get_doctors(db, skip=skip, limit=limit)
    return doctors

@router.get("/api/doctors/{doctor_id}", response_model=schemas.DoctorResponse)
def read_doctor_api(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_doctor = crud.get_doctor(db, doctor_id=doctor_id)
    if db_doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db_doctor

@router.put("/api/doctors/{doctor_id}", response_model=schemas.DoctorResponse)
def update_doctor_api(
    doctor_id: int,
    doctor: schemas.DoctorUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    db_doctor = crud.update_doctor(db, doctor_id=doctor_id, doctor_update=doctor)
    if db_doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db_doctor

@router.delete("/api/doctors/{doctor_id}", response_model=bool)
def delete_doctor_api(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_admin_role)
):
    success = crud.delete_doctor(db, doctor_id=doctor_id)
    if not success:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return success

@router.get("/api/doctors/{doctor_id}/schedule", response_model=List[schemas.DoctorScheduleResponse])
def read_doctor_schedule_api(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    schedules = crud.get_doctor_schedules(db, doctor_id)
    return schedules

@router.post("/api/doctors/schedule", response_model=schemas.DoctorScheduleResponse)
def create_doctor_schedule_api(
    schedule: schemas.DoctorScheduleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_doctor_role)
):
    doctor = crud.get_doctor_by_user_id(db, current_user.user_id)
    if not doctor or doctor.doctor_id != schedule.doctor_id:
        raise HTTPException(status_code=403, detail="Not authorized to create schedule for this doctor")
    
    return crud.create_schedule(db, schedule)
