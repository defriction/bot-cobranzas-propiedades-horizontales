FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Nota: Cambiamos COPY app ./app por COPY . . porque los archivos origen están en la raíz, no en una carpeta app/
COPY . .

ENV PYTHONPATH=/app
ENV TZ=America/Bogota

# Nota: Ajustamos uvicorn app.main:app a main:app por la misma razón jerárquica
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
