# Stage 1: Build the frontend static files
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Run the Flask backend
FROM python:3.11-slim
WORKDIR /app

# Expose Flask default port
EXPOSE 5000

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend codebase
COPY backend/ /app/backend/

# Copy static compiled frontend build
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

ENV FLASK_ENV=production

# Start Flask server
CMD ["python", "backend/app.py"]
