FROM python:3.11-slim

# Install LibreOffice & dependencies
RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-impress \
    libreoffice-writer \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app ./app

# Create folders
RUN mkdir -p uploads outputs

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
