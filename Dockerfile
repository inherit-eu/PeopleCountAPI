FROM python:3.13-slim

# Prevents Python from writing pyc files and buffers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (optional but common). Add build-essential only if you compile wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install dependencies first
COPY requirements /app/requirements
RUN pip install --no-cache-dir -r /app/requirements

# Copy app code
COPY ./auth/ /app/auth/
COPY ./model/ /app/model/
COPY ./util/ /app/util/
COPY ./route/ /app/route/
COPY ./database.py /app
COPY ./main.py /app

# Security: run as non-root
RUN useradd -m appuser
USER appuser

EXPOSE 8080

# IMPORTANT:
# Replace "main:app" with the correct module:app path for your project.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
