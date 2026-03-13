# Stage 1: Build the Vue Frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend source
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
# Build the production SPA
RUN npm run build


# Stage 2: Build the Python Backend & Serve
FROM python:3.11-slim

# Prevent Python from writing pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python requirements
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend source code
COPY backend/ /app/backend/

# Copy the built frontend artifacts from Stage 1
# Note: The backend's main.py expects frontend/dist to be located at DATA_DIR.parent / "frontend" / "dist"
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Prepare directories and settings
RUN mkdir -p /app/data/db /app/data/covers /app/data/pool

# Copy and prepare the entrypoint script
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Environment variables
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/db/metomi.db

# Expose the single unified port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
