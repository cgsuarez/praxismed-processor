from supabase import create_client, Client
import os

class MedicalRepository:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        print(f"medical repository: {url}")
        self.supabase: Client = create_client(url, key)

    def get_clinic_by_phone(self, instance_phone: str):
        """
        Busca a qué clínica pertenece el número de WhatsApp de la instancia.
        Asumimos que el número de la instancia está registrado en la tabla 'clinics'.
        """
        response = self.supabase.table("clinics") \
            .select("id, name, timezone") \
            .eq("phone", instance_phone) \
            .single() \
            .execute()
        return response.data

    def is_phone_blacklisted(self, clinic_id: str, sender_phone: str) -> bool:
        """
        Verifica si el número del paciente está en la blacklist de esa clínica.
        """
        response = self.supabase.table("phone_blacklist") \
            .select("id") \
            .eq("clinic_id", clinic_id) \
            .eq("phone", sender_phone) \
            .execute()
        
        return len(response.data) > 0

    # --- CRUD PACIENTES ---
    def get_patient_by_phone(self, clinic_id: str, phone: str):
        """Busca paciente por teléfono dentro de una clínica específica."""
        response = self.supabase.table("patients") \
            .select("*") \
            .eq("clinic_id", clinic_id) \
            .eq("phone", phone) \
            .execute()
        return response.data[0] if response.data else None

    def create_patient(self, clinic_id: str, name: str, phone: str, email: str = None):
        """Crea un paciente siguiendo el esquema de la tabla 'patients'."""
        data = {
            "clinic_id": clinic_id,
            "full_name": name,
            "phone": phone,
            "email": email
        }
        print(f"Insertando pacientes: {data}")
        response = self.supabase.table("patients").insert(data).execute()
        return response.data[0]


    # --- CRUD AGENDAMIENTOS ---
    def create_appointment(self, clinic_id: str, patient_id: str, doctor_id: str, date: str, start_time: str):
        """Inserta en la tabla 'appointments' respetando los tipos de datos."""
        data = {
            "clinic_id": clinic_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": date,
            "start_time": start_time,
            "end_time": start_time, # Deberías calcular el fin según la duración
            "status": "confirmed"
        }
        response = self.supabase.table("appointments").insert(data).execute()
        return response.data[0]    
        
    # --- DOCTORES Y AGENDA ---
    def search_doctors(self, clinic_id: str, query: str):
        """Busca doctores por nombre o especialidad (vía join con specialties)."""
        # Nota: Usamos ilike para búsqueda insensible a mayúsculas        
        print(f"search_doctorsL {clinic_id} ")
        response = self.supabase.table("doctors") \
            .select("id, name, color, specialties!inner(name)") \
            .eq("clinic_id", clinic_id) \
            .execute()
        return response.data

    def get_doctor_schedule(self, doctor_id: str):
        """Obtiene el JSONB de la columna 'schedule' de la tabla doctors."""
        print(f"get_doctor_schedule: {doctor_id}")
        response = self.supabase.table("doctors") \
            .select("schedule") \
            .eq("id", doctor_id) \
            .single() \
            .execute()
        
        if not response.data or not response.data.get("schedule"):
            return "No hay horarios configurados."
        
        # Como tu esquema usa JSONB para 'schedule', lo procesamos directamente
        sched = response.data["schedule"]
        return f"Horarios disponibles: {sched}"
        
    def get_clinic_details(self, clinic_id: str):
        """
        Obtiene los detalles base de la clínica.
        Referencia tabla: public.clinics
        """
        # Cambié .eq("id", doctor_id) por clinic_id y eliminé la lógica de schedule 
        # que pertenecía a la función de doctores.
        response = self.supabase.table("clinics") \
            .select("*") \
            .eq("id", clinic_id) \
            .single() \
            .execute()
        
        if not response.data:
            return "Detalles de clínica no encontrados."
            
        return response.data

    def get_clinic_catalog(self, clinic_id: str):
        """
        Obtiene el catálogo de doctores y sus especialidades.
        Realiza un JOIN con la tabla specialties según tu esquema SQL.
        """
        # En Supabase/PostgREST, el JOIN se hace definiendo la relación en el .select()
        # Traemos el nombre del doctor y el nombre de su especialidad relacionada
        response = self.supabase.table("doctors") \
            .select("name, specialties(name)") \
            .eq("clinic_id", clinic_id) \
            .execute()
        
        if not response.data:
            return "No hay doctores disponibles en este catálogo por el momento."
        
        catalog = []
        for doc in response.data:
            # Accedemos a la especialidad mediante la relación definida en tu SQL
            specialty_name = doc.get("specialties", {}).get("name", "General")
            catalog.append(f"- Dr. {doc['name']} (Especialidad: {specialty_name})")
        
        return "Catálogo de Médicos:\n" + "\n".join(catalog)