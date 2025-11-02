# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies and Microsoft ODBC Driver for SQL Server
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    apt-transport-https \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl https://packages.microsoft.com/config/debian/12/prod.list | tee /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y \
    msodbcsql18 \
    unixodbc \
    unixodbc-dev \
    odbcinst \
    libodbcinst2 \
    libpq-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create a real user home directory so CrewAI can write RAG/ChromaDB data
ARG UID=10001
RUN useradd -m -d /home/appuser -u ${UID} appuser

# Set HOME so libraries know where to store files
ENV HOME=/home/appuser
RUN mkdir -p /home/appuser/.local/share && chmod -R 777 /home/appuser

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt && \
    python -m pip install --upgrade crewai crewai-tools

USER appuser

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
