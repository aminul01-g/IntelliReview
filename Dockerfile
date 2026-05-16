# Stage 1: Build the React frontend
FROM node:20 as frontend-builder
WORKDIR /app/dashboard
COPY dashboard/package*.json ./
RUN npm install
COPY dashboard/ ./
RUN npm run build

# Stage 2: Build the FastAPI backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy files needed for Python dependencies
COPY requirements.txt pyproject.toml ./

# Install Python dependencies - try requirements.txt first, then pyproject.toml
RUN pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir .

# Copy application code
COPY . .

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/dashboard/dist /app/dashboard/dist

# Create necessary directories
RUN mkdir -p logs chroma_db

# Verify frontend build exists
RUN ls -la /app/dashboard/dist/ || { echo "ERROR: Frontend dist missing!"; exit 1; }

# Expose HF Spaces default port
EXPOSE 7860

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
