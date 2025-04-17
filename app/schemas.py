from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from datetime import datetime, date, time
from enum import Enum

# User schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: str
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ['patient', 'doctor', 'admin']:
            raise ValueError('Role must be patient, doctor, or admin')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    user_id: int
    role: str
    is_active: bool
    
    class Config:
        orm_mode = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Patient schemas
class PatientBase(BaseModel):
    name: str
    dob: Optional[date] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None

class PatientCreate(PatientBase):
    user_id: int

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None

class PatientResponse(PatientBase):
    patient_id: int
    user_id: int
    
    class Config:
        orm_mode = True

# Doctor schemas
class DoctorBase(BaseModel):
    name: str
    specialization_id: Optional[int] = None
    experience: Optional[int] = None
    contact: Optional[str] = None

class DoctorCreate(DoctorBase):
    user_id: int

class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    specialization_id: Optional[int] = None
    experience: Optional[int] = None
    contact: Optional[str] = None

class DoctorResponse(DoctorBase):
    doctor_id: int
    user_id: int
    
    class Config:
        orm_mode = True

# Admin schemas
class AdminBase(BaseModel):
    name: str
    contact: Optional[str] = None

class AdminCreate(AdminBase):
    user_id: int

class AdminUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None

class AdminResponse(AdminBase):
    admin_id: int
    user_id: int
    
    class Config:
        orm_mode = True

# Appointment schemas
class AppointmentStatus(str, Enum):
    scheduled = "scheduled"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"

class AppointmentBase(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_time: datetime
    reason: Optional[str] = None
    status: AppointmentStatus = AppointmentStatus.scheduled

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    appointment_time: Optional[datetime] = None
    reason: Optional[str] = None
    status: Optional[AppointmentStatus] = None

class AppointmentResponse(AppointmentBase):
    appointment_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Doctor Schedule schemas
class DoctorScheduleBase(BaseModel):
    doctor_id: int
    day: str
    start_time: time
    end_time: time
    is_available: bool = True

class DoctorScheduleCreate(DoctorScheduleBase):
    pass

class DoctorScheduleUpdate(BaseModel):
    day: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_available: Optional[bool] = None

class DoctorScheduleResponse(DoctorScheduleBase):
    schedule_id: int
    
    class Config:
        orm_mode = True

# Health Record schemas
class HealthRecordBase(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_id: Optional[int] = None
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None

class HealthRecordCreate(HealthRecordBase):
    pass

class HealthRecordUpdate(BaseModel):
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None

class HealthRecordResponse(HealthRecordBase):
    record_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Prescription schemas
class PrescriptionBase(BaseModel):
    record_id: int
    medication_name: str
    dosage: Optional[str] = None
    instructions: Optional[str] = None
    duration: Optional[str] = None

class PrescriptionCreate(PrescriptionBase):
    pass

class PrescriptionUpdate(BaseModel):
    medication_name: Optional[str] = None
    dosage: Optional[str] = None
    instructions: Optional[str] = None
    duration: Optional[str] = None

class PrescriptionResponse(PrescriptionBase):
    prescription_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# Test schemas
class TestStatus(str, Enum):
    ordered = "ordered"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"

class TestBase(BaseModel):
    record_id: int
    test_name: str
    status: TestStatus = TestStatus.ordered
    result: Optional[str] = None
    report_url: Optional[str] = None
    ordered_by: int

class TestCreate(TestBase):
    pass

class TestUpdate(BaseModel):
    test_name: Optional[str] = None
    status: Optional[TestStatus] = None
    result: Optional[str] = None
    report_url: Optional[str] = None

class TestResponse(TestBase):
    test_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Billing schemas
class BillingStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"

class BillingBase(BaseModel):
    patient_id: int
    appointment_id: int
    amount: float
    status: BillingStatus = BillingStatus.pending
    payment_method: Optional[str] = None

class BillingCreate(BillingBase):
    pass

class BillingUpdate(BaseModel):
    amount: Optional[float] = None
    status: Optional[BillingStatus] = None
    payment_method: Optional[str] = None

class BillingResponse(BillingBase):
    billing_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Feedback schemas
class FeedbackBase(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class FeedbackCreate(FeedbackBase):
    pass

class FeedbackUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None

class FeedbackResponse(FeedbackBase):
    feedback_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# Insurance schemas
class InsuranceBase(BaseModel):
    patient_id: int
    provider_name: str
    policy_number: str
    coverage_details: Optional[str] = None
    valid_until: Optional[date] = None

class InsuranceCreate(InsuranceBase):
    pass

class InsuranceUpdate(BaseModel):
    provider_name: Optional[str] = None
    policy_number: Optional[str] = None
    coverage_details: Optional[str] = None
    valid_until: Optional[date] = None

class InsuranceResponse(InsuranceBase):
    insurance_id: int
    
    class Config:
        orm_mode = True

# Notification schemas
class NotificationBase(BaseModel):
    user_id: int
    title: str
    message: str
    is_read: bool = False

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None

class NotificationResponse(NotificationBase):
    notification_id: int
    timestamp: datetime
    
    class Config:
        orm_mode = True

# Specialization schemas
class SpecializationBase(BaseModel):
    name: str
    description: Optional[str] = None

class SpecializationCreate(SpecializationBase):
    pass

class SpecializationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class SpecializationResponse(SpecializationBase):
    specialization_id: int
    
    class Config:
        orm_mode = True

# Combined schemas for registration
class PatientRegistration(BaseModel):
    email: EmailStr
    password: str
    name: str
    dob: Optional[date] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None

class DoctorRegistration(BaseModel):
    email: EmailStr
    password: str
    name: str
    specialization_id: Optional[int] = None
    experience: Optional[int] = None
    contact: Optional[str] = None

class AdminRegistration(BaseModel):
    email: EmailStr
    password: str
    name: str
    contact: Optional[str] = None
