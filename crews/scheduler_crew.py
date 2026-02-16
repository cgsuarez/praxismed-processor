# crews/appointment_crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crews.tools.db_tools import confirmar_y_agendar_cita

from pydantic import BaseModel

@CrewBase
class SchedulerCrew():
    """Crew para el Onboarding y Agendamiento"""
    
    agents_config = '../config/agents_scheduler.yaml'
    tasks_config = '../config/tasks_scheduler.yaml'

    def __init__(self, doctor_id: int, patient_id: str, date: str = None, summary: str = None):
        self.doctor_id = doctor_id
        self.patient_id = patient_id
        self.date = date
        self.summary = summary

    @agent
    def scheduler_agent(self) -> Agent:
        print(f"Configuraciones cargadas para agente calendarizador: {self.agents_config.keys()}")
        return Agent(
            config=self.agents_config['scheduling_agent'],
            #llm=self.llm
            allow_delegation = False,            
            input={
                'doctor_id': self.doctor_id,
                'patient_id': self.patient_id,
                'date': self.date,
                'summary': self.summary
            },        
            verbose=True,
        )

    @task
    def scheduler_task(self) -> Task:
        return Task(
            config=self.tasks_config['task_registrar_cita_final'],
            tools=[confirmar_y_agendar_cita],
            agent=self.scheduler_agent(),            
        )
    
  
    @crew
    def scheduler_crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
    