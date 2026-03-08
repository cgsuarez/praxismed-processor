import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from crews.medical_flow import MedicalBookingFlow
from dotenv import load_dotenv
from database.redis_manager import RedisManager
import logging
import requests
import json
import os

from database.repository import MedicalRepository

# Configuración de Logs para ver qué pasa en tiempo real
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="AI Medical Assistant API")
redis_manager = RedisManager()

repo = MedicalRepository()

EVOLUTION_API_URL = os.environ.get("EVOLUTION_API_URL")

@app.post("/webhook/evolution")
def evolution_webhook(data: dict): # Quitamos el 'async'
    print(f"Webhook recibido: {data}")

    try:
        instance_name = data.get('instance')        
        incoming_msg = data.get('data', {}).get('message', {}).get('conversation')
        remote_jid = data.get('data').get('key', {}).get('remoteJid', '')
        sender_phone = remote_jid.split('@')[0]
        print(f"Mensaje: {incoming_msg}")
        print(f"sender_phone: {sender_phone}")

        clinic = repo.get_clinic_by_name(instance_name)
        if not clinic:
                return {"status": "ignored", "reason": "clinic_not_found"}
            
        
        clinic_id = clinic['id']
        print(f"Clinic id founc: {clinic_id}")

        # 3. VALIDACIÓN DE BLACKLIST
        if not repo.is_phone_blacklisted(clinic_id, sender_phone):
            print(f"🚫 Acceso denegado: {sender_phone} está en la blacklist de {clinic['name']}")
            return {"status": "blocked", "reason": "phone_in_blacklist"}

        result = run_medical_flow_sync(clinic_id, sender_phone , incoming_msg)
        print(f"RESULTADO DEL FLOW: {result}")

        # Resolve the actual response dict from whatever kickoff() returned.
        # kickoff() may return: a CrewOutput (has .raw), a plain dict, or the
        # AppointmentState (has .pending_response when an early-return path fired).
        if hasattr(result, 'raw'):
            raw = result.raw
            result_flow = json.loads(raw) if isinstance(raw, str) else raw
        elif isinstance(result, dict):
            result_flow = result
        elif hasattr(result, 'pending_response') and result.pending_response:
            result_flow = result.pending_response
        else:
            result_flow = {"message": str(result)}

        print(f"RESULTADO DEL result_flow: {result_flow}")
        enviar_a_whatsapp(instance=instance_name, client_name=clinic['name'], number=sender_phone, text=result_flow)

        # Extraer campos de primer nivel para que el consumidor no tenga que parsear result
        message = result_flow.get("message") if isinstance(result_flow, dict) else str(result_flow)
        opciones = result_flow.get("opciones") if isinstance(result_flow, dict) else None
        doctores_disponibles = result_flow.get("doctores_disponibles") if isinstance(result_flow, dict) else None

        # Persistir la conversación y los mensajes
        _save_conversation_messages(
            clinic_id=clinic_id,
            sender_phone=sender_phone,
            patient_message=incoming_msg,
            agent_message=message,
        )

        return {
            "status": "success",
            "message": message,
            "opciones": opciones,
            "doctores_disponibles": doctores_disponibles,
            "result": result_flow
        }
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {"status": "error"}    
    #import json
    #import asyncio
    ## Obtenemos los datos de forma síncrona para debug
    ##body = asyncio.run(request.json())
    ##body = await request.json()
    #
    #try:
    #    #data = body.get('data', {})
    #    incoming_msg = data.get('message', {}).get('conversation')
    #    remote_jid = data.get('key', {}).get('remoteJid', '')
    #    sender_phone = remote_jid.split('@')[0]
#
    #    print(f"\n--- DEBUG INICIO ---")
    #    print(f"Mensaje: {incoming_msg}")
    #    
    #    # LLAMADA SÍNCRONA AL FLOW
    #    result = run_medical_flow_sync(sender_phone, incoming_msg)
    #    
    #    print(f"--- DEBUG FIN ---\n")
    #    return {"status": "success", "result": result}
#
    #except Exception as e:
    #    print(f"ERROR: {str(e)}")
    #    return {"status": "error"}

def run_medical_flow_sync(clinic_id, phone: str, message: str):
    """Ejecución síncrona para ver logs limpios."""
    flow = MedicalBookingFlow(clinic_id)

    result = flow.kickoff(inputs={
        "patient_phone": phone,
        "message": message
    })

    # When a flow method returns early with a plain dict, kickoff() may return None.
    # In that case, recover the response from the flow state directly.
    if result is None and flow.state.pending_response:
        result = flow.state.pending_response

    print(f"RESPUESTA DEL AGENTE: {result}")
    return result

def _save_conversation_messages(clinic_id: str, sender_phone: str,
                                patient_message: str, agent_message: str):
    """
    Persiste la conversación y los dos mensajes (paciente + agente) en Supabase.
    Se ejecuta en modo best-effort: los errores se loguean pero no detienen la respuesta.

    Convención de direction:
      outbound → mensaje enviado por el paciente (sale desde el paciente hacia el sistema)
      inbound  → mensaje enviado por el agente   (llega al paciente desde el sistema)
    """
    try:
        patient = repo.get_patient_by_phone(clinic_id, sender_phone)
        if not patient:
            print("_save_conversation_messages: paciente aún no registrado, saltando.")
            return

        patient_id = patient["id"]
        conversation = repo.get_or_create_conversation(clinic_id, patient_id)
        conv_id = conversation["id"]

        # 1. Mensaje del paciente (outbound)
        if patient_message:
            repo.save_message(conv_id, patient_message, "outbound")
            repo.update_conversation(conv_id, patient_message, increment_unread=True)

        # 2. Respuesta del agente (inbound)
        if agent_message:
            repo.save_message(conv_id, agent_message, "inbound")
            repo.update_conversation(conv_id, agent_message, increment_unread=False)

        print(f"Conversación {conv_id} actualizada con {2 if patient_message and agent_message else 1} mensaje(s).")
    except Exception as e:
        print(f"Error guardando conversación/mensajes: {e}")


def enviar_a_whatsapp(instance, client_name, number, text):
    # 1. Limpiamos el número (solo dígitos)
    #import re
    #number_clean = re.sub(r'\D', '', number)
    
    url = f"{EVOLUTION_API_URL}/message/sendText/{instance}"
    headers = {
        "Content-Type": "application/json",
        "apikey": client_name
    }
    
    # 2. Nueva estructura requerida por Evolution API v2
    payload = {
        "number": number,
        "options": {
            "delay": 1200,
            "presence": "composing"
        },
        "textMessage": {
            "text": str(text) # <-- Aquí es donde debe ir el texto ahora
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"✅ Intento de envío a {number}: {response.status_code}")
        if response.status_code != 201 and response.status_code != 200:
            print(f"❌ Error detalle: {response.text}")
    except Exception as e:
        print(f"❌ Error de conexión con Evolution API: {e}")


if __name__ == "__main__":
    # Asegúrate de tener REDIS_HOST en tu .env o localmente
    uvicorn.run(app, host="0.0.0.0", port=8000)