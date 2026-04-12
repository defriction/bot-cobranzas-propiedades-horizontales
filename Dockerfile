FROM python:3.11-slim

# Configuración óptima de Python en contenedores
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configuración de zona horaria (Crucial para APScheduler)
ENV TZ=America/Bogota

WORKDIR /app

# Instalar primero librerías del sistema si fueran necesarias
RUN apt-get update && apt-get install -y tzdata && \
    ln -fs /usr/share/zoneinfo/America/Bogota /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código fuente al contenedor
COPY . .

EXPOSE 8000

# Comando principal
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
