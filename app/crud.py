from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from app import models, schemas
from app.security import get_password_hash, verify_password

# User CRUD operations
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.user_id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        password_hash=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate):
    db_user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if db_user:
        update_data = user_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    db_user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if db_user:
        if db_user.role == "patient":
            patient = db.query(models.Patient).filter(models.Patient.user_id == user_id).first()
            if patient:
                db.delete(patient)
        elif db_user.role == "doctor":
            doctor = db.query(models.Doctor).filter(models.Doctor.user_id == user_id).first()
            if doctor:
                db.delete(doctor)
        elif db_user.role == "admin":
            admin = db.query(models.Admin).filter(models.Admin.user_id == user_id).first()
            if admin:
                db.delete(admin)
        db.delete(db_user)
        db.commit()
        return True
    return False

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

# Patient CRUD operations
def get_patient(db: Session, patient_id: int):
    return db.query(models.Patient).filter(models.Patient.patient_id == patient_id).first()

def get_patient_by_user_id(db: Session, user_id: int):
    return db.query(models.Patient).filter(models.Patient.user_id == user_id).first()

def get_patients(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Patient).offset(skip).limit(limit).all()

def create_patient(db: Session, patient: schemas.PatientCreate):
    db_patient = models.Patient(**patient.dict())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

def update_patient(db: Session, patient_id: int, patient_update: schemas.PatientUpdate):
    db_patient = db.query(models.Patient).filter(models.Patient.patient_id == patient_id).first()
    if db_patient:
        update_data = patient_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_patient, key, value)
        db.commit()
        db.refresh(db_patient)
    return db_patient

def delete_patient(db: Session, patient_id: int):
    db_patient = db.query(models.Patient).filter(models.Patient.patient_id == patient_id).first()
    if db_patient:
        db.delete(db_patient)
        db.commit()
        return True
    return False

# Doctor CRUD operations
def get_doctor(db: Session, doctor_id: int):
    return db.query(models.Doctor).filter(models.Doctor.doctor_id == doctor_id).first()

def get_doctor_by_user_id(db: Session, user_id: int):
    return db.query(models.Doctor).filter(models.Doctor.user_id == user_id).first()

def get_doctors(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Doctor).offset(skip).limit(limit).all()

def create_doctor(db: Session, doctor: schemas.DoctorCreate):
    db_doctor = models.Doctor(**doctor.dict())
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor

def update_doctor(db: Session, doctor_id: int, doctor_update: schemas.DoctorUpdate):
    db_doctor = db.query(models.Doctor).filter(models.Doctor.doctor_id == doctor_id).first()
    if db_doctor:
        update_data = doctor_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_doctor, key, value)
        db.commit()
        db.refresh(db_doctor)
    return db_doctor

def delete_doctor(db: Session, doctor_id: int):
    db_doctor = db.query(models.Doctor).filter(models.Doctor.doctor_id == doctor_id).first()
    if db_doctor:
        db.delete(db_doctor)
        db.commit()
        return True
    return False

# Admin CRUD operations
def get_admin(db: Session, admin_id: int):
    return db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()

def get_admin_by_user_id(db: Session, user_id: int):
    return db.query(models.Admin).filter(models.Admin.user_id == user_id).first()

def get_admins(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Admin).offset(skip).limit(limit).all()

def create_admin(db: Session, admin: schemas.AdminCreate):
    db_admin = models.Admin(**admin.dict())
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin

def update_admin(db: Session, admin_id: int, admin_update: schemas.AdminUpdate):
    db_admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
    if db_admin:
        update_data = admin_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_admin, key, value)
        db.commit()
        db.refresh(db_admin)
    return db_admin

def delete_admin(db: Session, admin_id: int):
    db_admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
    if db_admin:
        db.delete(db_admin)
        db.commit()
        return True
    return False

# Appointment CRUD operations
def get_appointment(db: Session, appointment_id: int):
    return db.query(models.Appointment).filter(models.Appointment.appointment_id == appointment_id).first()

def get_appointments(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Appointment).offset(skip).limit(limit).all()

def get_patient_appointments(db: Session, patient_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Appointment).filter(models.Appointment.patient_id == patient_id).offset(skip).limit(limit).all()

def get_doctor_appointments(db: Session, doctor_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Appointment).filter(models.Appointment.doctor_id == doctor_id).offset(skip).limit(limit).all()

def create_appointment(db: Session, appointment: schemas.AppointmentCreate):
    db_appointment = models.Appointment(**appointment.dict())
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

def update_appointment(db: Session, appointment_id: int, appointment_update: schemas.AppointmentUpdate):
    db_appointment = db.query(models.Appointment).filter(models.Appointment.appointment_id == appointment_id).first()
    if db_appointment:
        update_data = appointment_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_appointment, key, value)
        db.commit()
        db.refresh(db_appointment)
    return db_appointment

def delete_appointment(db: Session, appointment_id: int):
    db_appointment = db.query(models.Appointment).filter(models.Appointment.appointment_id == appointment_id).first()
    if db_appointment:
        db.delete(db_appointment)
        db.commit()
        return True
    return False

# Doctor Schedule CRUD operations
def get_schedule(db: Session, schedule_id: int):
    return db.query(models.DoctorSchedule).filter(models.DoctorSchedule.schedule_id == schedule_id).first()

def get_doctor_schedules(db: Session, doctor_id: int):
    return db.query(models.DoctorSchedule).filter(models.DoctorSchedule.doctor_id == doctor_id).all()

def get_available_slots(db: Session, doctor_id: int, date: datetime.date):
    # Get the day of the week
    day_of_week = date.strftime("%A").lower()
    
    # Get the doctor's schedule for that day
    schedules = db.query(models.DoctorSchedule).filter(
        models.DoctorSchedule.doctor_id == doctor_id,
        models.DoctorSchedule.day == day_of_week,
        models.DoctorSchedule.is_available == True
    ).all()
    
    if not schedules:
        return []
    
    # Calculate time slots (e.g., 30-minute intervals)
    all_slots = []
    for schedule in schedules:
        current_time = datetime.combine(date, schedule.start_time)
        end_time = datetime.combine(date, schedule.end_time)
        
        while current_time < end_time:
            slot_end = current_time + timedelta(minutes=30)
            if slot_end <= end_time:
                all_slots.append((current_time, slot_end))
            current_time = slot_end
    
    # Get existing appointments for that doctor on that day
    start_of_day = datetime.combine(date, datetime.min.time())
    end_of_day = datetime.combine(date, datetime.max.time())
    
    existing_appointments = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.appointment_time >= start_of_day,
        models.Appointment.appointment_time <= end_of_day,
        models.Appointment.status.in_([models.AppointmentStatus.scheduled, models.AppointmentStatus.confirmed])
    ).all()
    
    # Filter out slots that overlap with existing appointments
    available_slots = []
    for slot_start, slot_end in all_slots:
        is_available = True
        for appt in existing_appointments:
            appt_time = appt.appointment_time
            # Check if appointment overlaps with this slot
            if slot_start <= appt_time < slot_end:
                is_available = False
                break
        
        if is_available:
            available_slots.append((slot_start, slot_end))
    
    return available_slots

def create_schedule(db: Session, schedule: schemas.DoctorScheduleCreate):
    db_schedule = models.DoctorSchedule(**schedule.dict())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

def update_schedule(db: Session, schedule_id: int, schedule_update: schemas.DoctorScheduleUpdate):
    db_schedule = db.query(models.DoctorSchedule).filter(models.DoctorSchedule.schedule_id == schedule_id).first()
    if db_schedule:
        update_data = schedule_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_schedule, key, value)
        db.commit()
        db.refresh(db_schedule)
    return db_schedule

def delete_schedule(db: Session, schedule_id: int):
    db_schedule = db.query(models.DoctorSchedule).filter(models.DoctorSchedule.schedule_id == schedule_id).first()
    if db_schedule:
        db.delete(db_schedule)
        db.commit()
        return True
    return False

# Health Record CRUD operations
def get_health_record(db: Session, record_id: int):
    return db.query(models.HealthRecord).filter(models.HealthRecord.record_id == record_id).first()

def get_patient_health_records(db: Session, patient_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.HealthRecord).filter(models.HealthRecord.patient_id == patient_id).offset(skip).limit(limit).all()

def create_health_record(db: Session, health_record: schemas.HealthRecordCreate):
    db_health_record = models.HealthRecord(**health_record.dict())
    db.add(db_health_record)
    db.commit()
    db.refresh(db_health_record)
    return db_health_record

def update_health_record(db: Session, record_id: int, health_record_update: schemas.HealthRecordUpdate):
    db_health_record = db.query(models.HealthRecord).filter(models.HealthRecord.record_id == record_id).first()
    if db_health_record:
        update_data = health_record_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_health_record, key, value)
        db.commit()
        db.refresh(db_health_record)
    return db_health_record

def delete_health_record(db: Session, record_id: int):
    db_health_record = db.query(models.HealthRecord).filter(models.HealthRecord.record_id == record_id).first()
    if db_health_record:
        db.delete(db_health_record)
        db.commit()
        return True
    return False

# Prescription CRUD operations
def get_prescription(db: Session, prescription_id: int):
    return db.query(models.Prescription).filter(models.Prescription.prescription_id == prescription_id).first()

def get_record_prescriptions(db: Session, record_id: int):
    return db.query(models.Prescription).filter(models.Prescription.record_id == record_id).all()

def create_prescription(db: Session, prescription: schemas.PrescriptionCreate):
    db_prescription = models.Prescription(**prescription.dict())
    db.add(db_prescription)
    db.commit()
    db.refresh(db_prescription)
    return db_prescription

def update_prescription(db: Session, prescription_id: int, prescription_update: schemas.PrescriptionUpdate):
    db_prescription = db.query(models.Prescription).filter(models.Prescription.prescription_id == prescription_id).first()
    if db_prescription:
        update_data = prescription_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_prescription, key, value)
        db.commit()
        db.refresh(db_prescription)
    return db_prescription

def delete_prescription(db: Session, prescription_id: int):
    db_prescription = db.query(models.Prescription).filter(models.Prescription.prescription_id == prescription_id).first()
    if db_prescription:
        db.delete(db_prescription)
        db.commit()
        return True
    return False

# Test CRUD operations
def get_test(db: Session, test_id: int):
    return db.query(models.Test).filter(models.Test.test_id == test_id).first()

def get_record_tests(db: Session, record_id: int):
    return db.query(models.Test).filter(models.Test.record_id == record_id).all()

def create_test(db: Session, test: schemas.TestCreate):
    db_test = models.Test(**test.dict())
    db.add(db_test)
    db.commit()
    db.refresh(db_test)
    return db_test

def update_test(db: Session, test_id: int, test_update: schemas.TestUpdate):
    db_test = db.query(models.Test).filter(models.Test.test_id == test_id).first()
    if db_test:
        update_data = test_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_test, key, value)
        db.commit()
        db.refresh(db_test)
    return db_test

def delete_test(db: Session, test_id: int):
    db_test = db.query(models.Test).filter(models.Test.test_id == test_id).first()
    if db_test:
        db.delete(db_test)
        db.commit()
        return True
    return False

# Billing CRUD operations
def get_billing(db: Session, billing_id: int):
    return db.query(models.Billing).filter(models.Billing.billing_id == billing_id).first()

def get_patient_billings(db: Session, patient_id: int):
    return db.query(models.Billing).filter(models.Billing.patient_id == patient_id).all()

def create_billing(db: Session, billing: schemas.BillingCreate):
    db_billing = models.Billing(**billing.dict())
    db.add(db_billing)
    db.commit()
    db.refresh(db_billing)
    return db_billing

def update_billing(db: Session, billing_id: int, billing_update: schemas.BillingUpdate):
    db_billing = db.query(models.Billing).filter(models.Billing.billing_id == billing_id).first()
    if db_billing:
        update_data = billing_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_billing, key, value)
        db.commit()
        db.refresh(db_billing)
    return db_billing

def delete_billing(db: Session, billing_id: int):
    db_billing = db.query(models.Billing).filter(models.Billing.billing_id == billing_id).first()
    if db_billing:
        db.delete(db_billing)
        db.commit()
        return True
    return False

# Feedback CRUD operations
def get_feedback(db: Session, feedback_id: int):
    return db.query(models.Feedback).filter(models.Feedback.feedback_id == feedback_id).first()

def get_doctor_feedbacks(db: Session, doctor_id: int):
    return db.query(models.Feedback).filter(models.Feedback.doctor_id == doctor_id).all()

def get_patient_feedbacks(db: Session, patient_id: int):
    return db.query(models.Feedback).filter(models.Feedback.patient_id == patient_id).all()

def create_feedback(db: Session, feedback: schemas.FeedbackCreate):
    db_feedback = models.Feedback(**feedback.dict())
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

def update_feedback(db: Session, feedback_id: int, feedback_update: schemas.FeedbackUpdate):
    db_feedback = db.query(models.Feedback).filter(models.Feedback.feedback_id == feedback_id).first()
    if db_feedback:
        update_data = feedback_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_feedback, key, value)
        db.commit()
        db.refresh(db_feedback)
    return db_feedback

def delete_feedback(db: Session, feedback_id: int):
    db_feedback = db.query(models.Feedback).filter(models.Feedback.feedback_id == feedback_id).first()
    if db_feedback:
        db.delete(db_feedback)
        db.commit()
        return True
    return False

# Insurance CRUD operations
def get_insurance(db: Session, insurance_id: int):
    return db.query(models.Insurance).filter(models.Insurance.insurance_id == insurance_id).first()

def get_patient_insurances(db: Session, patient_id: int):
    return db.query(models.Insurance).filter(models.Insurance.patient_id == patient_id).all()

def create_insurance(db: Session, insurance: schemas.InsuranceCreate):
    db_insurance = models.Insurance(**insurance.dict())
    db.add(db_insurance)
    db.commit()
    db.refresh(db_insurance)
    return db_insurance

def update_insurance(db: Session, insurance_id: int, insurance_update: schemas.InsuranceUpdate):
    db_insurance = db.query(models.Insurance).filter(models.Insurance.insurance_id == insurance_id).first()
    if db_insurance:
        update_data = insurance_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_insurance, key, value)
        db.commit()
        db.refresh(db_insurance)
    return db_insurance

def delete_insurance(db: Session, insurance_id: int):
    db_insurance = db.query(models.Insurance).filter(models.Insurance.insurance_id == insurance_id).first()
    if db_insurance:
        db.delete(db_insurance)
        db.commit()
        return True
    return False

# Notification CRUD operations
def get_notification(db: Session, notification_id: int):
    return db.query(models.Notification).filter(models.Notification.notification_id == notification_id).first()

def get_user_notifications(db: Session, user_id: int):
    return db.query(models.Notification).filter(models.Notification.user_id == user_id).all()

def create_notification(db: Session, notification: schemas.NotificationCreate):
    db_notification = models.Notification(**notification.dict())
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

def update_notification(db: Session, notification_id: int, notification_update: schemas.NotificationUpdate):
    db_notification = db.query(models.Notification).filter(models.Notification.notification_id == notification_id).first()
    if db_notification:
        update_data = notification_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_notification, key, value)
        db.commit()
        db.refresh(db_notification)
    return db_notification

def delete_notification(db: Session, notification_id: int):
    db_notification = db.query(models.Notification).filter(models.Notification.notification_id == notification_id).first()
    if db_notification:
        db.delete(db_notification)
        db.commit()
        return True
    return False

# Specialization CRUD operations
def get_specialization(db: Session, specialization_id: int):
    return db.query(models.Specialization).filter(models.Specialization.specialization_id == specialization_id).first()

def get_specializations(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Specialization).offset(skip).limit(limit).all()

def create_specialization(db: Session, specialization: schemas.SpecializationCreate):
    db_specialization = models.Specialization(**specialization.dict())
    db.add(db_specialization)
    db.commit()
    db.refresh(db_specialization)
    return db_specialization

def update_specialization(db: Session, specialization_id: int, specialization_update: schemas.SpecializationUpdate):
    db_specialization = db.query(models.Specialization).filter(models.Specialization.specialization_id == specialization_id).first()
    if db_specialization:
        update_data = specialization_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_specialization, key, value)
        db.commit()
        db.refresh(db_specialization)
    return db_specialization

def delete_specialization(db: Session, specialization_id: int):
    db_specialization = db.query(models.Specialization).filter(models.Specialization.specialization_id == specialization_id).first()
    if db_specialization:
        db.delete(db_specialization)
        db.commit()
        return True
    return False

# Registration operations
def register_patient(db: Session, registration: schemas.PatientRegistration):
    # Create user
    user = create_user(db, schemas.UserCreate(
        email=registration.email,
        password=registration.password,
        role="patient"
    ))
    
    # Create patient
    patient_data = registration.dict(exclude={"email", "password"})
    patient = create_patient(db, schemas.PatientCreate(user_id=user.user_id, **patient_data))
    
    return patient

def register_doctor(db: Session, registration: schemas.DoctorRegistration):
    # Create user
    user = create_user(db, schemas.UserCreate(
        email=registration.email,
        password=registration.password,
        role="doctor"
    ))
    
    # Create doctor
    doctor_data = registration.dict(exclude={"email", "password"})
    doctor = create_doctor(db, schemas.DoctorCreate(user_id=user.user_id, **doctor_data))
    
    return doctor

def register_admin(db: Session, registration: schemas.AdminRegistration):
    # Create user
    user = create_user(db, schemas.UserCreate(
        email=registration.email,
        password=registration.password,
        role="admin"
    ))
    
    # Create admin
    admin_data = registration.dict(exclude={"email", "password"})
    admin = create_admin(db, schemas.AdminCreate(user_id=user.user_id, **admin_data))
    
    return admin
