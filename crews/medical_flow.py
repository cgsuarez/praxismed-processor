import json
from crewai.crew import Crew
from crewai.crews import CrewOutput
from crewai.flow.flow import Flow, start, router, listen
from pydantic import BaseModel, ConfigDict
from database.repository import MedicalRepository
from crews.onboarding_crew import OnboardingCrew 
from crews.scheduler_crew import SchedulerCrew
from crews.receptionist_crew import ReceptionistCrew
from database.redis_manager import RedisManager
from typing import Optional, Any
from fastapi.encoders import jsonable_encoder
from datetime import date

class BookingStepOutput(BaseModel):
    next_step: str  # Ejemplo: 'BOOKING_DATE', 'BOOKING_HOUR', 'CONFIRMATION_PENDING'
    extracted_data: dict  # { "specialty": "Odontología", "doctor_id": 12 }
    response_message: str  # El mensaje que Evolution API enviará al usuario
    is_complete: bool  # True si ya tenemos todo para insertar en Postgres


class PatientRegistrationModel(BaseModel):
    full_name: str
    email: str
    is_complete: bool

class AppointmentState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    patient_phone: str = ""
    patient_exists: bool = False
    patient_data: dict = {}
    appointment_details: str = ""
    clinic_details: Optional[Any] = None
    message: str = ""
    clinic_id: str = "" 
    current_step: str = ""
    history: list = []
    metadata: dict = {}
    message: str = ""
    available_catalog: str = ""

class MedicalBookingFlow(Flow[AppointmentState]):

    def __init__(self, clinic_id: str):
        print("**** init ")
        super().__init__()
        self.clinic_id = clinic_id
        self.redis = RedisManager()    


    @start()
    def handle_incoming_webhook(self):
        # 1. Recuperar contexto de Redis
        print(f"****handle_incoming_webhook {self.state.patient_phone} ")
        session = self.redis.get_session(self.state.patient_phone)
        print(f"Sesión recuperada de Redis: {session}")
        self.state.clinic_id = self.clinic_id
        repo = MedicalRepository()
        patient = repo.get_patient_by_phone(self.clinic_id, self.state.patient_phone)
        patient_data = None
        print(f"******* patient: {patient} for patientphone: {self.state.patient_phone}")
        if patient:
            patient_data = {
                "full_name": patient["full_name"],
                "email": patient["email"],
                "id": patient["id"]
            }
            print(f"*** patient data: {patient_data}")

        if not session:

            print("Cargando catálogo de la clínica...")
            
            # Guardamos el catálogo en el estado del flujo
            self.state.available_catalog = repo.get_clinic_catalog(self.state.clinic_id)
            print(f"Obteniendo detalles de la clínica...{self.state.available_catalog}")
            #Guardamos detalles de la clínica
            self.state.clinic_details = repo.get_clinic_details(self.state.clinic_id)
            print(f"Detalles de la clínica cargados. {self.state.clinic_details}")                                   

            data_serializable = jsonable_encoder(self.state.clinic_details)
            json_string = json.dumps(data_serializable)
            # Es un usuario nuevo o sesión expirada
            session = {
                "clinic_details": json_string,
                "available_catalog": self.state.available_catalog,
                "current_step": "START",
                "patient_phone": self.state.patient_phone,
                "metadata": {"phone": self.state.patient_phone},
                "patient_data": patient_data,
                "history": []
            }
            
            self.redis.save_session(self.state.patient_phone, session)
        else:            
            session["patient_data"] = patient_data            
            self.redis.save_session(self.state.patient_phone, session)            


        # 2. Inyectar datos de Redis al estado del Flow


        
        print(f"init current_Step: {session['current_step']}")
        self.state.current_step = session["current_step"]
        self.state.history = session["history"]
        self.state.metadata = session["metadata"]
        self.state.clinic_details = json.loads(session["clinic_details"])
        self.state.available_catalog = session["available_catalog"]
        self.state.patient_data = session["patient_data"]        
        return "route_request"
#
#
    @router(handle_incoming_webhook) # Viene del paso donde cargamos Redis
    def dynamic_router(self):
        print(f"Router initiated. Current step: {self.state.current_step}")
        status = self.state.current_step
        
        
        # 1. Si no tiene cuenta o está en registro
        if status in ["START", "ONBOARDING"]:
            print("**** La cuenta no esta registrada")
            if self.state.patient_data is not None:
                print("El paciente existe procedo a guardar la sesion con el nuevo estado")
                session_data = self.redis.get_session(self.state.patient_phone)
                session_data["current_step"] = "BOOKING_SPECIALTY"
                print(f"Antes de rgrabar session data: {session_data}")
                self.redis.save_session(self.state.patient_phone, session_data)
                self.state.current_step = session_data["current_step"]
                return "go_booking"
            return "go_onboarding"
        
        # 2. Si ya está registrado y quiere una cita
        if status in ["BOOKING_SPECIALTY", "BOOKING_DATE", "BOOKING_HOUR"]:
            print("**** La cuenta YA esta registrada")
            return "go_booking"
        
        if status in ["SCHEDULING"]:
            print("*** Realizar calendarization")
            return "go_schedule"
        
        if status in ["COMPLETED"]:
            return "finish_flow"
            
        # 3. Si solo está preguntando algo general
        if "QUERY" in status:
            return "go_support"
        return "go_receptionist_general"

    @listen("go_onboarding")
    def go_onboarding_method(self):
        # 3. Decidir qué Crew usar según el paso guardado en Redis
        clinic_details = self.state.clinic_details        
        print(f"Iniciando OnboardingCrew para clínica: {clinic_details['name']}")
        if self.state.current_step in ["START", "ONBOARDING"]:
            print("Antes de get metadata")
            chat_history = self.state.metadata.get("chat_history", "No hay mensajes previos.")
            print("Luego de get metadata")

            result = OnboardingCrew(clinic_id = clinic_details['id'], clinic_name = clinic_details['name']).onboarding_crew().kickoff(inputs={
                "message": self.state.message,
                "history": self.state.history,                
                "clinic_name": clinic_details['name'],
                "patient_phone": self.state.patient_phone,
                "chat_history": self.state.metadata.get("chat_history", [])                
            })
            
            print(f"CREW Result Type: {type(result)}")
            print(f"CREW Result: {result.raw}")
            

            if isinstance(result, CrewOutput) or 'raw' in result:
                if isinstance(result.raw, str):
                    print(f"CREW raw: {result.raw}")
                else:
                    print(f"CREW raw (dict): {result.raw}")
                json_result = result.raw if isinstance(result.raw, str) else json.loads(result.raw)
            else:
                print("CREW result has no 'raw' attribute.")
                json_result = {
                    "message": result
                }
            # 4. Actualizar Redis con la respuesta del Agente
            # Asumimos que el agente devuelve el siguiente paso y datos extraídos

            print(f"json_result Result Type: {type(json_result)}")
            

            

            
            patient_data = {}

            if(isinstance(json_result, str)):                    
                json_result = json.loads(json_result)
            print(f"json_result Result: {json_result}")
            if "missing_fields" in json_result and len(json_result["missing_fields"])!=0:
                print("******* 2")
                print("Faltan datos para completar el registro.")
                next_step = "ONBOARDING"
            else:
                print("******* 3")                
                # se graba los datos del paciente                
                repo = MedicalRepository()

                repo.create_patient(self.clinic_id,
                                    json_result.get("full_name"), 
                                    self.state.patient_phone,
                                    json_result.get("email"))
                

                next_step = "BOOKING_SPECIALTY"
                patient_data = {
                    "full_name": json_result.get("full_name"),
                    "email": json_result.get("email")
                }
                print(f"Datos del paciente registrados: {patient_data}")

            new_history = f"{chat_history}\nUsuario: {self.state.message}\nAsistente: {result.raw}"
            self.state.metadata["chat_history"] = new_history
            
            self.redis.save_session(self.state.patient_phone, {
                "current_step": next_step,
                "metadata": self.state.metadata,
                "clinic_details": json.dumps(self.state.clinic_details),
                "patient_phone": self.state.patient_phone,
                "available_catalog": self.state.available_catalog,
                "patient_data": patient_data,
                "history": self.state.history + [{"role": "user", "content": self.state.message}]
            })
        
        print("Onboarding completed.")
        return result
    
    @listen("go_booking")
    def go_booking_method(self):
        # 3. Decidir qué Crew usar según el paso guardado en Redis
        
        clinic_details = self.state.clinic_details        
        print(f"Iniciando Receptionist Crew para clínica: {clinic_details['name']}")
        next_step = self.state.current_step
        metadata = self.state.metadata
        if self.state.current_step in ["BOOKING_SPECIALTY", "BOOKING_DATE", "BOOKING_HOUR"]:
            print(f"***** bookindg 1 {self.state.metadata}")
            chat_history = self.state.metadata.get("chat_history", "No hay mensajes previos.")
            print("***** bookindg 1.1")
            session = self.redis.get_session(self.state.patient_phone)
            print("***** bookindg 2")
            patient_data = session.get("patient_data", {})
            print(f"Patient Data from session: {patient_data}")

            result = ReceptionistCrew(
                clinic_id = clinic_details['id'],
                clinic_name = clinic_details['name'], 
                patient_name = patient_data.get("full_name", "Paciente")).receptionist_crew().kickoff(inputs={
                "message": self.state.message,
                "history": self.state.history,      
                "clinic_id": self.clinic_id,          
                "clinic_name": clinic_details['name'],
                "patient_phone": self.state.patient_phone,
                "patient_name": patient_data.get("full_name", "Paciente"),  
                "catalog": self.state.available_catalog,
                "current_date": date.today().isoformat(),
                "chat_history": self.state.metadata.get("chat_history", [])                
            })

            new_history = f"{chat_history}\nUsuario: {self.state.message}\nAsistente: {result.raw}"
            self.state.metadata["chat_history"] = new_history
            
            print(f"CREW Receptionist Result Type: {type(result)}")
            print(f"CREW Receptionist Result: {result}")
            print(f"CREW Receptionist raw: {result.raw}")

            
            data = result.to_dict() 
            
            # 3. Lógica de Reconocimiento: ¿Están los campos obligatorios?
            if data.get('doctor_id') and data.get('patient_id') and data.get('date'):
                print("✅ Datos completos encontrados. Cambiando a estado CALENDARIZACIÓN.")                
                metadata['doctor_id'] = data.get('doctor_id')                
                metadata['patient_id'] = data.get('patient_id')                
                metadata['date'] = data.get('date')                                
                next_step = "SCHEDULING"

            json_result = result.raw if isinstance(result.raw, str) else json.loads(result.raw)
            ## 4. Actualizar Redis con la respuesta del Agente
            ## Asumimos que el agente devuelve el siguiente paso y datos extraídos

            print(f"json_result Result Type: {type(json_result)}")
            print(f"json_result Result: {json_result}")

            #next_step = "BOOKING_SPECIALTY"
            #if "missing_fields" in json_result:
            #    print("Faltan datos para completar el registro.")
            #    next_step = "ONBOARDING"
            #

            
            session = self.redis.get_session(self.state.patient_phone)
            session["current_step"] = next_step
            session["metadata"] = metadata
        
            session["history"] = self.state.history + [{"role": "user", "content": self.state.message}]

            self.redis.save_session(self.state.patient_phone, session)
        
        print("booking completed.")        
        return result
#


    @listen("go_schedule")
    def go_schedule_method(self):
        
        # Recuperamos los IDs que guardamos en pasos anteriores en el estado
        d_id = self.state.metadata.get("doctor_id")
        c_id = self.state.clinic_id
        p_id = self.state.patient_data['id']
        date = self.state.metadata.get("date")
        summary = self.state.metadata.get("summary")

        
        print(f"p_id: {p_id} doctorid: {d_id} date: {date}")
        result = SchedulerCrew(
                doctor_id = d_id,
                patient_id = p_id,
                date = date,
                summary = summary
               ).scheduler_crew().kickoff(inputs={
                "clinic_id": c_id,
                "doctor_id": d_id,
                "patient_id": p_id,                
                "date": date,
                "summary": summary
            })
        json_result = result.raw if isinstance(result.raw, str) else json.loads(result.raw)
        # --- AQUÍ ESTÁ LA SOLUCIÓN ---
        # 3. Actualizar el estado en Redis para romper el bucle
        print("✅ Agendamiento finalizado. Reseteando estado a START.")
        
        session = self.redis.get_session(self.state.patient_phone)
        if session:
            print("Ingreso completado")
            session["current_step"] = "COMPLETED"  # O "COMPLETED"
            # Limpiamos la metadata temporal de la cita para la próxima vez
            session["metadata"].pop("doctor_id", None)
            session["metadata"].pop("date", None)
            session["metadata"]["message"] = json_result
            self.state.message = json_result
            self.redis.save_session(self.state.patient_phone, session)

        
        # Actualizamos el estado local del Flow
        self.state.current_step = "COMPLETED"
        print("--- FIN DEL METODO GO_SCHEDULE ---")
        return result

    @listen("finish_flow")
    def finish_flow_method(self):
        print("--- FLUJO FINALIZADO ---")
        session = self.redis.get_session(self.state.patient_phone)
        self.state.current_step = "START"
        session["current_step"] = "START"  # O "COMPLETED"
        self.redis.save_session(self.state.patient_phone, session)
        # Opcional: Podrías borrar la metadata aquí para que la próxima 
        # interacción del usuario meses después sea limpia.
        return "Se ha realizado el agendamiento. Desea algo mas?"

#def run_flow():
#    flow = MedicalBookingFlow()
#    
#    # El kickoff devuelve el estado final del flujo
#    #flow.state.patient_phone = "123456789"
#    #flow.state.appointment_details = "Cita de cardiología para el lunes"
#    result = flow.kickoff(inputs={
#        "patient_phone": "123456781",
#        "message": "Cita de cardiología para el lunes"
#    })
#    
#    print("\n" + "="*30)
#    print("RESULTADO FINAL DEL AGENDAMIENTO:")
#    print(result)
#    print("="*30)
#
#if __name__ == "__main__":
#    run_flow()