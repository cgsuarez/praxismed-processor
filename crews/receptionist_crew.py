# crews/appointment_crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crews.tools.db_tools import buscar_doctor, consultar_agenda_doctor
from datetime import date

from pydantic import BaseModel

class AppointmentTransfer(BaseModel):
    doctor_id: str
    patient_id: str
    date: str  # Formato sugerido: YYYY-MM-DD HH:MM
    summary: str # Breve resumen para el siguiente agente


@CrewBase
class ReceptionistCrew():
    """Crew para el Onboarding y Agendamiento"""
    
    agents_config = '../config/agents_receptionist.yaml'
    tasks_config = '../config/tasks_receptionist.yaml'

    def __init__(self, clinic_id: int, clinic_name: str, patient_name: str = None, catalog_list: [] = None):
        self.clinic_id = clinic_id
        self.clinic_name = clinic_name
        self.patient_name = patient_name
        self.catalog_list = catalog_list

    @agent
    def receptionist_agent(self) -> Agent:
        print(f"Configuraciones cargadas para agente recepcionista: {self.agents_config.keys()}")
        return Agent(
            config=self.agents_config['receptionist_agent'],
            #llm=self.llm
            #allow_delegation = False,
            input={
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



    @crew
    def receptionist_crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
    