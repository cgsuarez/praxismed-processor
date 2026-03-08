from crewai.tools import tool
from database.repository import MedicalRepository
from datetime import date, datetime, timedelta

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
    
    print(f"se encontraron resultados: {len(resultados)}")
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

@tool("verificar_cita_existente")
def verificar_cita_existente(clinic_id: str, patient_id: str):
    """
    Verifica si el paciente ya tiene una cita confirmada (status='confirmed') en la clínica.
    Retorna los datos de la cita si existe, o indica que no hay cita activa.
    """
    repository = MedicalRepository()
    cita = repository.get_confirmed_appointment(clinic_id, patient_id)
    if not cita:
        return "El paciente no tiene citas confirmadas actualmente."
    doctor_name = cita.get("doctors", {}).get("name", "el doctor") if cita.get("doctors") else "el doctor"
    fecha = cita.get("appointment_date", "")
    hora = cita.get("start_time", "")
    return f"Cita encontrada | ID: {cita['id']} | Fecha: {fecha} | Hora: {hora} | Doctor: {doctor_name}"

@tool("cancelar_cita")
def cancelar_cita(appointment_id: str):
    """
    Cancela la cita del paciente actualizando el estado a 'cancelled'.
    Recibe el appointment_id (UUID) de la cita a cancelar.
    """
    repository = MedicalRepository()
    result = repository.cancel_appointment(appointment_id)
    if result:
        return f"Cita cancelada exitosamente. ID: {result['id']}"
    return "No se pudo cancelar la cita. Verifique el ID proporcionado."


_DAY_NAMES_ES = {
    "monday": "lunes", "tuesday": "martes", "wednesday": "miércoles",
    "thursday": "jueves", "friday": "viernes", "saturday": "sábado", "sunday": "domingo"
}
_MONTH_NAMES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

@tool("consultar_agenda_doctor")
def consultar_agenda_doctor(doctor_id: str):
    """
    Consulta la disponibilidad de un doctor para los próximos 8 días (hoy + 7 días).
    Genera turnos en bloques de 30 minutos dentro del horario habilitado de cada día.
    Retorna un dict con dos campos:
      - agenda_disponible: {"YYYY-MM-DD": ["HH:MM", ...], ...}  (para validación interna)
      - dias_disponibles:  [{"fecha": "YYYY-MM-DD", "etiqueta": "lunes 2 de marzo", "slots": ["HH:MM", ...]}, ...]
    Usa siempre dias_disponibles para redactar mensajes al paciente; nunca derives nombres
    de días a partir de la fecha ISO.
    """
    print(f"*** Consultando agenda del doctor desde tool con id {doctor_id}***")
    repository = MedicalRepository()
    raw_schedule = repository.get_doctor_schedule(doctor_id)

    if not raw_schedule:
        return "El doctor no tiene horarios disponibles."

    today = date.today()
    now = datetime.now()
    agenda_disponible = {}
    dias_disponibles = []

    for offset in range(8):  # hoy hasta hoy + 7 días
        target_date = today + timedelta(days=offset)
        day_name = target_date.strftime("%A").lower()  # "monday", "friday", etc.
        day_cfg = raw_schedule.get(day_name, {})

        if not day_cfg.get("enabled", False):
            continue

        from_h, from_m = map(int, day_cfg["from"].split(":"))
        to_h, to_m = map(int, day_cfg["to"].split(":"))

        slot = datetime(target_date.year, target_date.month, target_date.day, from_h, from_m)
        end = datetime(target_date.year, target_date.month, target_date.day, to_h, to_m)

        # Para el día de hoy, descartar slots que ya pasaron
        if offset == 0:
            while slot <= now:
                slot += timedelta(minutes=30)

        slots = []
        while slot < end:
            slots.append(slot.strftime("%H:%M"))
            slot += timedelta(minutes=30)

        if slots:
            date_iso = target_date.isoformat()
            day_es = _DAY_NAMES_ES[day_name]
            month_es = _MONTH_NAMES_ES[target_date.month]
            etiqueta = f"{day_es} {target_date.day} de {month_es}"

            agenda_disponible[date_iso] = slots
            dias_disponibles.append({
                "fecha": date_iso,
                "etiqueta": etiqueta,
                "slots": slots
            })

    if not agenda_disponible:
        return "El doctor no tiene horarios disponibles en los próximos 7 días."

    # Lista plana de opciones para uso en UI interactiva (botones / listas de WhatsApp)
    opciones = [
        {"label": f"{entry['etiqueta']} - {slot}", "value": f"{entry['fecha']} {slot}"}
        for entry in dias_disponibles
        for slot in entry["slots"]
    ]

    result = {
        "agenda_disponible": agenda_disponible,
        "dias_disponibles": dias_disponibles,
        "opciones": opciones
    }
    print(f"*** Slots disponibles generados: {result} ***")
    return result