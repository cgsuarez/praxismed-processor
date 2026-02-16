# Usamos una imagen ligera de Python 3.12 (más estable para CrewAI que 3.13 por ahora)
FROM python:3.12-slim

# Evita que Python genere archivos .pyc y permite ver logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Configuración de Supabase
ENV SUPABASE_URL=http://supabase.url
ENV SUPABASE_KEY=supabasekey
ENV EVOLUTION_API_URL=evolutionapi
ENV REDIS_URL=http://redis.url
ENV OPENAI_API_KEY=testkey

# Directorio de trabajo
WORKDIR /app

# Instalamos dependencias del sistema necesarias para algunas librerías de IA y Postgres
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiamos solo el requirements primero para aprovechar el cache de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . .

# Exponemos el puerto que usa Render (por defecto suele ser el 10000)
EXPOSE 8000

# Comando para arrancar FastAPI con Uvicorn
# Usamos 0.0.0.0 para que sea accesible desde fuera del contenedor
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]