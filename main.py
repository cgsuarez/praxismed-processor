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

        # 3. VALIDACIÓN DE BLACKLIST
        if repo.is_phone_blacklisted(clinic_id, sender_phone):
            print(f"🚫 Acceso denegado: {sender_phone} está en la blacklist de {clinic['name']}")
            return {"status": "blocked", "reason": "phone_in_blacklist"}

        result = run_medical_flow_sync(clinic_id, sender_phone , incoming_msg)
        print(f"RESULTADO DEL FLOW: {result}")
        
        result_flow = json.loads(result.raw) if 'raw' in result else result
        print(f"RESULTADO DEL result_flow: {result}")
        #enviar_a_whatsapp(instance=instance_name, client_name=clinic['name'], number=sender_phone, text=result_flow)

        return {"status": "success", "result": result_flow}
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
    
    # .kickoff() sin await ejecutará el flujo de forma bloqueante
    # Nota: Dependiendo de tu versión de CrewAI, si kickoff es corrutina,
    # puedes usar .kickoff().result() o simplemente llamar a la crew directamente.
    result = flow.kickoff(inputs={
        "patient_phone": phone,
        "message": message
    })
    
    print(f"RESPUESTA DEL AGENTE: {result}")


    return result

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