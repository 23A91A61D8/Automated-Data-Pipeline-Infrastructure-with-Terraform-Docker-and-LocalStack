# ==============================================================================
# Dockerfile - Automated ETL Application
# Lightweight, reproducible container packaging for Python ETL pipeline
# ==============================================================================

# Use official lightweight Python 3.10 slim base image
FROM python:3.10-slim

# Set environment variables for Python runtime optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the container working directory
WORKDIR /app

# Copy dependency definition first to leverage Docker layer caching
COPY src/requirements.txt .

# Install Python dependencies without caching pip wheels to minimize image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ .

# Default command executing the ETL application
CMD ["python", "etl_script.py"]
