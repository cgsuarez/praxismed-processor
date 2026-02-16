from crewai.tools import tool
from database.repository import MedicalRepository

# Instancia global del repositorio
repo = MedicalRepository()

@tool("buscar_doctor_por_nombre_o_especialidad")
def buscar_doctor(clinic_id: str, query: str):
    """
    Busca la lista de médicos y especialidades disponibles para una clínica específica.
    Recibe un clinic_id (UUID) y retorna un texto con el catálogo de doctores.
    """
    print(f"Buscar doctor: {clinic_id}")
    """Busca doctores disponibles en la clínica por nombre o especialidad."""
    resultados = repo.search_doctors(clinic_id, query)
    if not resultados:
        return "No se encontraron doctores."
    
    return "\n".join([
        f"ID: {d['id']} | Dr. {d['name']} | Especialidad: {d['specialties']['name']}" 
        for d in resultados
    ])

@tool("confirmar_y_agendar_cita")
def confirmar_y_agendar_cita(clinic_id: str, patient_id: str, doctor_id: str, date: str, time: str):
    """
    Registra la cita en Supabase.
    Formatos: date (YYYY-MM-DD), time (HH:MM)
    """
    try:
        nueva_cita = repo.create_appointment(clinic_id, patient_id, doctor_id, date, time)
        return f"Cita confirmada. ID: {nueva_cita['id']}"
    except Exception as e:
        return f"Error al agendar: {str(e)}"

@tool("verificar_paciente")
def verificar_paciente(clinic_id: str, phone: str):
    """Verifica si el paciente ya existe en esta clínica."""
    paciente = repo.get_patient_by_phone(clinic_id, phone)
    if paciente:
        return f"Paciente encontrado: {paciente['full_name']} (ID: {paciente['id']})"
    return "Paciente no registrado."


@tool("consultar_agenda_doctor")
def consultar_agenda_doctor(doctor_id: str):
    """
    Consulta la disponibilidad y agenda de un doctor específico usando su ID.
    Útil después de haber identificado qué doctor necesita el paciente.
    """
    print(f"*** Consultando agenda del doctor desde tool con id {doctor_id}***")
    repository = MedicalRepository()
    agenda = repository.get_doctor_schedule(doctor_id) # Tu método de base de datos
    return agenda if agenda else "El doctor no tiene horarios disponibles."