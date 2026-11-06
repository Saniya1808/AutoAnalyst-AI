# Official Microsoft Playwright image matching playwright==1.64.1 on Ubuntu Noble (24.04 LTS)
# Includes preinstalled Chromium, all Linux OS shared libraries (libnss3, libasound2, etc.), and fonts
FROM mcr.microsoft.com/playwright/python:v1.64.1-noble

# Set Python environment flags and default port
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=10000

# Set application working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose container port
EXPOSE 10000

# Start Uvicorn bound to 0.0.0.0 and dynamic $PORT (falling back to 10000)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]

