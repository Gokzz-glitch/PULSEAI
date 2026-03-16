# PulseAI Production Deployment

Production-ready Docker deployment for PulseAI backend and frontend, pinned to Python 3.10.11.

## What Was Added
- Dockerized backend with Python 3.10.11 base image.
- Dockerized frontend with Vite build + Nginx runtime.
- Production Docker Compose file.
- GitHub Actions workflow for Docker build + smoke test.
- Screenshot placeholders for deployment documentation.

## Project Structure
- backend/Dockerfile
- frontend/Dockerfile
- frontend/nginx.conf
- docker-compose.prod.yml
- .github/workflows/docker-ci.yml
- .env.example
- docs/screenshots/backend-health.svg
- docs/screenshots/docker-containers.svg
- docs/screenshots/github-actions.svg

## Prerequisites
- Docker Desktop installed and running.
- Port 8000 and 8080 available.

## 1. Configure Environment
Copy env template and set values:

```powershell
Copy-Item .env.example .env
```

Optional:
- Set COLAB_INFERENCE_URL to route inference to Colab endpoint.
- Keep it empty to use local backend inference path.

## 2. Build and Run (Production)

```powershell
docker compose -f docker-compose.prod.yml up --build -d
```

Verify:

```powershell
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

App URLs:
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000

## 3. Stop Stack

```powershell
docker compose -f docker-compose.prod.yml down
```

## 4. GitHub Actions (Docker CI)
Workflow file:
- .github/workflows/docker-ci.yml

Pipeline validates:
- Backend Docker build
- Frontend Docker build
- Backend health endpoint smoke test

## Screenshots
Deployment screenshots currently use placeholders in SVG format:

![Backend Health](docs/screenshots/backend-health.svg)
![Docker Containers](docs/screenshots/docker-containers.svg)
![GitHub Actions](docs/screenshots/github-actions.svg)

Replace these with real screenshots from your machine and GitHub Actions run:
- docs/screenshots/backend-health.png
- docs/screenshots/docker-containers.png
- docs/screenshots/github-actions.png

Then update README image links if needed.

## Push to GitHub

```powershell
git add .
git commit -m "Add production Docker deployment with Python 3.10.11 and CI"
git push origin main
```

## Notes
- Current workspace does not have Docker CLI available yet, so runtime verification must be done after Docker Desktop installation.
- Backend currently supports local mode and Colab bridge mode via COLAB_INFERENCE_URL.
