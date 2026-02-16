import redis
import json
import os
from typing import Optional, Any

class RedisManager:
    def __init__(self):
        # Configuración por variables de entorno o valores por defecto
        redis_url = os.getenv("REDIS_URL")
        self.client = redis.from_url(
            redis_url, 
            decode_responses=True,
            socket_timeout=5,     # Evita que tu app se quede colgada si falla la red
            retry_on_timeout=True
        )        
        self.ttl = 3600  # Tiempo de vida: 1 hora

    def save_session(self, phone: str, state_data: dict):
        """Guarda o actualiza el estado de la conversación."""
        key = f"session:{phone}"
        self.client.set(key, json.dumps(state_data), ex=self.ttl)

    def get_session(self, phone: str) -> Optional[dict]:
        """Recupera la sesión actual."""
        data = self.client.get(f"session:{phone}")
        return json.loads(data) if data else None

    def update_history(self, phone: str, role: str, content: str):
        """Añade un mensaje al historial sin borrar el resto del estado."""
        session = self.get_session(phone)
        if session:
            if "history" not in session:
                session["history"] = []
            session["history"].append({"role": role, "content": content})
            # Mantener solo los últimos 10 mensajes para no saturar el contexto
            session["history"] = session["history"][-10:]
            self.save_session(phone, session)

    def delete_session(self, phone: str):
        """Elimina la sesión (usar al finalizar onboarding o agendamiento)."""
        self.client.delete(f"session:{phone}")