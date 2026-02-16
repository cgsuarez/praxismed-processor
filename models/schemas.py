from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Time
from sqlalchemy.orm import relationship
from database.connection import Base
import datetime

class Clinic(Base):
    __tablename__ = 'clinics'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(Text)
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relaciones
    doctors = relationship("Doctor", back_populates="clinic")
    appointments = relationship("Appointment", back_populates="clinic")


class Doctor(Base):
    __tablename__ = 'doctors'
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey('clinics.id', ondelete="SET NULL"))
    full_name = Column(String(100), nullable=False)
    specialty = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(100), unique=True)
    is_active = Column(Boolean, default=True)

    # Relaciones
    clinic = relationship("Clinic", back_populates="doctors")
    schedules = relationship("DoctorSchedule", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")


class Patient(Base):
    __tablename__ = 'patients'
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    email = Column(String(100), unique=True)
    date_of_birth = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relaciones
    appointments = relationship("Appointment", back_populates="patient")


class DoctorSchedule(Base):
    __tablename__ = 'doctor_schedules'
    
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey('doctors.id', ondelete="CASCADE"))
    day_of_week = Column(Integer)  # 0=Sunday, 1=Monday...
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_blocked = Column(Boolean, default=False)
    description = Column(String(50))

    # Relaciones
    doctor = relationship("Doctor", back_populates="schedules")


class Appointment(Base):
    __tablename__ = 'appointments'
    
    id = Column(Integer, primary_key=True, index=True)
    appointment_date = Column(DateTime, nullable=False)
    patient_id = Column(Integer, ForeignKey('patients.id', ondelete="CASCADE"))
    doctor_id = Column(Integer, ForeignKey('doctors.id', ondelete="CASCADE"))
    clinic_id = Column(Integer, ForeignKey('clinics.id'))
    status = Column(String(20), default='Scheduled') # Scheduled, Completed, Cancelled
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relaciones
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    clinic = relationship("Clinic", back_populates="appointments")