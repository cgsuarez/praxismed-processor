# crews/appointment_crew.py
import os
import yaml
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crews.tools.db_tools import buscar_doctor, consultar_agenda_doctor, confirmar_y_agendar_cita, cancelar_cita
from datetime import date
from typing import Optional

from pydantic import BaseModel

class AppointmentTransfer(BaseModel):
    doctor_id: Optional[str] = None
    patient_id: Optional[str] = None
    clinic_id: Optional[str] = None
    date: Optional[str] = None  # Formato: YYYY-MM-DD HH:MM
    summary: str = ""
    missing_information: Optional[str] = None   # "pending_doctor_selection" | "pending_time_selection" | null
    response_message: Optional[str] = None      # Mensaje para reenviar al paciente en ese caso
    doctores_disponibles: Optional[list] = None # [{doctor_id, doctor_name, especialidad}] cuando hay múltiples
    opciones: Optional[list] = None             # [{label, value}] para UI — doctores O slots según el contexto

class AgentScheduleRegister(BaseModel):
    result: bool
    message: str
    missing_information: Optional[str] = None   # Propagado desde AppointmentTransfer si aplica
    doctores_disponibles: Optional[list] = None  # Propagado desde AppointmentTransfer si aplica
    opciones: Optional[list] = None              # Propagado desde AppointmentTransfer si aplica


@CrewBase
class ReceptionistCrew():
    """Crew para el Onboarding y Agendamiento"""
    
    agents_config = '../config/agents_receptionist.yaml'
    tasks_config = '../config/tasks_receptionist.yaml'

    def __init__(self, clinic_id: int, clinic_name: str, patient_name: str = None, catalog_list:[] = None, patient_id: str = None):
        self.clinic_id = clinic_id
        self.clinic_name = clinic_name
        self.patient_name = patient_name
        self.catalog_list = catalog_list
        self.patient_id = patient_id

    @agent
    def receptionist_agent(self) -> Agent:
        print(f"Configuraciones cargadas para agente recepcionista: {self.agents_config.keys()}")
        return Agent(
            config=self.agents_config['receptionist_agent'],
            #llm=self.llm
            #allow_delegation = False,
            input={
                'patient_id': self.patient_id,
                'clinic_id': self.clinic_id,
                'clinic_name': self.clinic_name,
                'patient_name': self.patient_name,
                'catalog': self.catalog_list,
                'current_date': date.today()
            },        
            verbose=True,
        )

    @agent
    def coordinador_agenda(self) -> Agent:
        print(f"Configuraciones cargadas para coordinador_agenda: {self.agents_config.keys()}")
        return Agent(
            config=self.agents_config['coordinador_agenda'],
            #llm=self.llm
            #allow_delegation = False,
            input={
                'patient_id': self.patient_id,
                'clinic_id': self.clinic_id,
                'clinic_name': self.clinic_name,
                'patient_name': self.patient_name,
                'current_date': date.today()
            },            
            verbose=True,
        )
    
    @agent
    def scheduling_agent(self) -> Agent:
        print(f"Configuraciones cargadas para calendarizador_agenda: {self.agents_config.keys()}")
        return Agent(
            config=self.agents_config['scheduling_agent'],
            #llm=self.llm
            #allow_delegation = False,
            input={
                'patient_id': self.patient_id,
                'clinic_id': self.clinic_id,
                'clinic_name': self.clinic_name,
                'patient_name': self.patient_name,
                'current_date': date.today()
            },            
            verbose=True,
        )

    @task
    def receptionist_task(self) -> Task:
        return Task(
            config=self.tasks_config['tarea_triaje_y_recepcion'],
            agent=self.receptionist_agent(),            
        )
    
    @task
    def find_doctor_task(self) -> Task:
        return Task(
            config=self.tasks_config['tarea_encontrar_agenda_doctor'],
            tools=[buscar_doctor, consultar_agenda_doctor],
            agent=self.receptionist_agent(),                
        )

    

    @task
    def coordinador_agenda_task(self) -> Task:
        return Task(
            config=self.tasks_config['tarea_gestion_agenda'],
            agent=self.coordinador_agenda(),  
            output_json=AppointmentTransfer # Forzamos el formato          
        )
    
    @task
    def registar_cita_task(self) -> Task:
        return Task(
            config=self.tasks_config['task_registrar_cita_final'],
            agent=self.scheduling_agent(),  
            tools=[confirmar_y_agendar_cita],
            output_json=AgentScheduleRegister # Forzamos el formato          
        )



    @crew
    def receptionist_crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )


class ExistingAppointmentAction(BaseModel):
    action: str  # "cancelled" | "reschedule" | "pending"
    message: str


_CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')


class ExistingAppointmentCrew():
    """Crew para gestionar citas ya agendadas (cancelar o reagendar).
    Construido manualmente para evitar que @CrewBase intente auto-descubrir
    todos los agentes del YAML compartido."""

    def __init__(self, clinic_id: str, clinic_name: str, patient_name: str = None,
                 appointment_id: str = None, appointment_info: str = None):
        self.clinic_id = clinic_id
        self.clinic_name = clinic_name
        self.patient_name = patient_name or "Paciente"
        self.appointment_id = appointment_id
        self.appointment_info = appointment_info

        with open(os.path.join(_CONFIG_DIR, 'agents_receptionist.yaml'), 'r', encoding='utf-8') as f:
            self._agents_cfg = yaml.safe_load(f)
        with open(os.path.join(_CONFIG_DIR, 'tasks_receptionist.yaml'), 'r', encoding='utf-8') as f:
            self._tasks_cfg = yaml.safe_load(f)

    def existing_appointment_crew(self) -> Crew:
        agent = Agent(
            config=self._agents_cfg['receptionist_agent'],
            verbose=True,
        )
        task = Task(
            config=self._tasks_cfg['tarea_gestionar_cita_existente'],
            tools=[cancelar_cita],
            agent=agent,
            output_json=ExistingAppointmentAction,
        )
        return Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )
