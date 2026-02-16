# crews/appointment_crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

@CrewBase
class OnboardingCrew():
    """Crew para el Onboarding y Agendamiento"""
    
    agents_config = 'config/agents_onboarding.yaml'
    tasks_config = 'config/tasks_onboarding.yaml'

    def __init__(self, clinic_id: int, clinic_name: str):
        self.clinic_id = clinic_id
        self.clinic_name = clinic_name        

    #@agent
    #def patient_onboarding_agent(self) -> Agent:
    #    print(f"Configuraciones cargadas: {self.agents_config.keys()}")
    #    return Agent(
    #        config=self.agents_config['patient_onboarding_agent'],
    #        #llm=self.llm
    #        #allow_delegation = False,
    #        input={
    #            'clinic_id': self.clinic_id,
    #            'clinic_name': self.clinic_name
    #        },            
    #        verbose=True,
    #    )

  
    @task
    def capture_patient_data_task(self) -> Task:
        return Task(
            config=self.tasks_config['capture_patient_data_task'],
            agent=self.patient_onboarding_agent(),            
            #output_json=PatientRegistrationModel # Opcional: Usar Pydantic para validar el JSON
        )
    
    @task
    def validate_registration_data_task(self) -> Task:
        return Task(
            config=self.tasks_config['validate_registration_data_task'],
            
        )   


    @crew
    def onboarding_crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
    