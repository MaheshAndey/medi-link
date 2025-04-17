from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Float, Text, Date, Time, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="user", uselist=False)
    doctor = relationship("Doctor", back_populates="user", uselist=False)
    admin = relationship("Admin", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user")

class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), unique=True)
    name = Column(String(255), nullable=False)
    dob = Column(Date)
    gender = Column(String(50))
    contact = Column(String(100))
    address = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    health_records = relationship("HealthRecord", back_populates="patient")
    billings = relationship("Billing", back_populates="patient")
    feedbacks = relationship("Feedback", back_populates="patient")
    insurances = relationship("Insurance", back_populates="patient")

class Doctor(Base):
    __tablename__ = "doctors"

    doctor_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), unique=True)
    name = Column(String(255), nullable=False)
    specialization_id = Column(Integer, ForeignKey("specializations.specialization_id"))
    experience = Column(Integer)
    contact = Column(String(100))
    
    # Relationships
    user = relationship("User", back_populates="doctor")
    specialization = relationship("Specialization", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")
    health_records = relationship("HealthRecord", back_populates="doctor")
    schedules = relationship("DoctorSchedule", back_populates="doctor")
    feedbacks = relationship("Feedback", back_populates="doctor")

class Admin(Base):
    __tablename__ = "admins"

    admin_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), unique=True)
    name = Column(String(255), nullable=False)
    contact = Column(String(100))
    
    # Relationships
    user = relationship("User", back_populates="admin")

class AppointmentStatus(str, enum.Enum):
    scheduled = "scheduled"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"

class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"))
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"))
    appointment_time = Column(DateTime, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.scheduled)
    reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    health_records = relationship("HealthRecord", back_populates="appointment")
    billings = relationship("Billing", back_populates="appointment")
    feedbacks = relationship("Feedback", back_populates="appointment")

class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"

    schedule_id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"))
    day = Column(String(20), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_available = Column(Boolean, default=True)
    
    # Relationships
    doctor = relationship("Doctor", back_populates="schedules")

class HealthRecord(Base):
    __tablename__ = "health_records"

    record_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"))
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"))
    appointment_id = Column(Integer, ForeignKey("appointments.appointment_id"))
    symptoms = Column(Text)
    diagnosis = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="health_records")
    doctor = relationship("Doctor", back_populates="health_records")
    appointment = relationship("Appointment", back_populates="health_records")
    prescriptions = relationship("Prescription", back_populates="health_record")
    tests = relationship("Test", back_populates="health_record")

class Prescription(Base):
    __tablename__ = "prescriptions"

    prescription_id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("health_records.record_id"))
    medication_name = Column(String(255), nullable=False)
    dosage = Column(String(100))
    instructions = Column(Text)
    duration = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    health_record = relationship("HealthRecord", back_populates="prescriptions")

class TestStatus(str, enum.Enum):
    ordered = "ordered"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"

class Test(Base):
    __tablename__ = "tests"

    test_id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("health_records.record_id"))
    test_name = Column(String(255), nullable=False)
    status = Column(Enum(TestStatus), default=TestStatus.ordered)
    result = Column(Text)
    report_url = Column(String(255))
    ordered_by = Column(Integer, ForeignKey("doctors.doctor_id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    health_record = relationship("HealthRecord", back_populates="tests")
    doctor = relationship("Doctor", foreign_keys=[ordered_by])

class BillingStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"

class Billing(Base):
    __tablename__ = "billings"

    billing_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"))
    appointment_id = Column(Integer, ForeignKey("appointments.appointment_id"))
    amount = Column(Float, nullable=False)
    status = Column(Enum(BillingStatus), default=BillingStatus.pending)
    payment_method = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="billings")
    appointment = relationship("Appointment", back_populates="billings")

class Feedback(Base):
    __tablename__ = "feedbacks"

    feedback_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"))
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"))
    appointment_id = Column(Integer, ForeignKey("appointments.appointment_id"))
    rating = Column(Integer)
    comment = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="feedbacks")
    doctor = relationship("Doctor", back_populates="feedbacks")
    appointment = relationship("Appointment", back_populates="feedbacks")

class Insurance(Base):
    __tablename__ = "insurances"

    insurance_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"))
    provider_name = Column(String(255), nullable=False)
    policy_number = Column(String(100), nullable=False)
    coverage_details = Column(Text)
    valid_until = Column(Date)
    
    # Relationships
    patient = relationship("Patient", back_populates="insurances")

class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    is_read = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="notifications")

class Specialization(Base):
    __tablename__ = "specializations"

    specialization_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    
    # Relationships
    doctors = relationship("Doctor", back_populates="specialization")
