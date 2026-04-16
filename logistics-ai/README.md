# Logistics AI

Logistics AI is a full-stack logistics monitoring and decision-support platform. It combines a React dashboard, a FastAPI backend, deterministic ML-style scoring, an LLM-backed agentic decision layer, Redis-powered caching and queueing, and a Grafana Loki logging stack to help operators monitor shipments, evaluate risk, and simulate interventions.

## What the repository contains

- A React + TypeScript frontend for live shipment visibility, alerts, simulation, and authentication
- A FastAPI backend that aggregates shipment signals, scores risk, generates recommendations, and exposes APIs
- A deterministic ML scoring pipeline for ETA, delay probability, anomaly score, and operational risk
- An agentic AI layer that converts shipment context into action recommendations using Groq, with a deterministic fallback engine
- Redis-backed cache and queue behavior used during normal request processing
- A Celery worker for optional background evaluation jobs
- Structured JSON application logging shipped through Promtail to Loki and visualized in Grafana

## Architecture at a glance

```text
React/Vite frontend
  -> FastAPI API layer
  -> Monitoring orchestration service
  -> Data enrichment services
       - shipment seeds
       - weather
       - congestion
       - news
  -> ML scoring layer
       - ETA prediction
       - delay probability
       - anomaly score
       - risk score
  -> Agentic AI layer
       - prompt builder
       - Groq client
       - response parser
       - fallback engine
  -> Simulation and ripple analysis
  -> Redis cache / queue + optional Celery worker
  -> Structured logs -> Promtail -> Loki -> Grafana
```

## Tech stack

### Frontend

- React 18
- TypeScript
- Vite
- Leaflet and React Leaflet for shipment map views

### Backend

- FastAPI
- Uvicorn
- Pydantic
- HTTPX
- PyJWT
- Cryptography / Fernet

### Data, caching, and async

- Redis for cache and queue operations
- Celery for background processing
- SQLite for active auth, refresh token, and MFA persistence
- MySQL/SQLAlchemy scaffolding is also present in the codebase for future or partial database expansion

### ML and AI

- Deterministic Python scoring modules for ETA, delay, anomaly, and risk
- Groq-hosted LLM integration for shipment action recommendations
- Deterministic fallback decision engine when LLM output is unavailable or invalid

### Observability and operations

- Docker Compose
- Grafana Loki
- Promtail
- Grafana
- Structured JSON backend logging

## Repository structure

```text
logistics-ai/
  backend/
    app/
      agent/        # Groq + fallback decision engine
      api/          # FastAPI routes
      ml/           # Deterministic scoring modules
      models/       # Pydantic/domain models
      services/     # Monitoring, simulation, enrichment, Redis helpers
    data/           # JSON seed data and local SQLite DB
    Dockerfile
    requirements.txt
    worker.py       # Celery worker entrypoint
  frontend/
    src/
      components/   # Dashboard and auth UI
      context/      # Auth and MFA state
      hooks/        # Dashboard polling
      services/     # API clients
      pages/        # Main views
    Dockerfile
    package.json
  observability/
    loki-config.yml
    promtail-config.yml
    grafana/
  docker-compose.yml
```

## Core product flow

1. The frontend authenticates the user and requests shipment, alert, summary, and decision data from the backend.
2. The backend loads shipment seed data and enriches it with weather, congestion, and news signals.
3. The ML layer converts that operational context into machine-readable outputs such as predicted ETA, delay probability, anomaly score, and risk score.
4. The agentic AI layer turns that enriched shipment state into an action recommendation, confidence score, reason, and alert payload.
5. The simulation layer estimates the downstream effect of taking that action, including ripple impact on dependent shipments.
6. Redis accelerates repeated reads and stores queue events generated during refresh or background workflows.
7. Structured request and domain logs are collected by Promtail, stored in Loki, and surfaced in Grafana dashboards.

## ML layer

The ML layer in this project is a deterministic scoring pipeline rather than a separately trained model-serving platform.

### Inputs

- Shipment seed data
- Shipment criticality and priority
- Weather status
- Congestion level
- News tags and disruption signals

### Processing modules

- `backend/app/ml/delay_predictor.py`
- `backend/app/ml/anomaly_detector.py`
- `backend/app/ml/risk_scorer.py`
- `backend/app/ml/eta_predictor.py`
- `backend/app/ml/scoring.py`

### Outputs

- `eta_prediction`
- `delay_probability`
- `anomaly_score`
- `risk_score`

### Role in the system

This layer answers the operational question: "How risky, delayed, or abnormal is this shipment right now?" Its outputs are then passed into the agentic AI layer and the simulation layer.

## Agentic AI layer

The agentic layer is responsible for turning operational state into a recommended action.

### Main components

- `backend/app/agent/decision_engine.py`
- `backend/app/agent/prompt_builder.py`
- `backend/app/agent/groq_client.py`
- `backend/app/agent/response_parser.py`
- `backend/app/agent/fallback_engine.py`

### Inputs

- Shipment identity and current status
- Route and destination context
- ML outputs from the scoring layer
- Weather, congestion, and news signals
- Alternate carrier availability and dependency information

### Outputs

- Recommended `action`
- `confidence`
- Human-readable `reason`
- `alert`
- `source` showing whether the answer came from the LLM or the fallback engine

### Execution path

1. The backend builds a `DecisionContext`.
2. A constrained logistics optimizer prompt is generated.
3. The prompt is sent to Groq using JSON-oriented output handling.
4. The response is parsed into a structured `DecisionOutput`.
5. If the model response fails validation or the upstream AI call is unavailable, the fallback engine produces a deterministic recommendation.

### Important implementation note

The current production path is Groq-first with fallback logic. A Gemini client exists in the repository, but it is not the active decision path in the main engine.

## Simulation and ripple analysis

After a recommendation is produced, the platform can estimate its downstream effect.

### Inputs

- Selected shipment
- Recommended or hypothetical action
- Related shipments and dependency context

### Outputs

- Simulated ETA shift
- Risk and delay delta
- Affected downstream shipments
- Ripple summary for operator review

This logic lives primarily in:

- `backend/app/services/simulation_service.py`
- `backend/app/services/ripple_engine.py`
- `backend/app/services/monitoring_service.py`

## Data flow through the program

### Data sources

- `backend/data/shipments.json`
- `backend/data/congestion.json`
- `backend/data/news.json`
- OpenWeather API when configured, with local fallback behavior when it is not

### Request lifecycle

1. A request reaches FastAPI through routes in `backend/app/api/`.
2. The route calls a service such as `monitoring_service`, `simulation_service`, or `shipment_service`.
3. The service merges seed data and live signal data.
4. The ML scoring layer computes shipment metrics.
5. The decision engine generates an AI-assisted recommendation.
6. The service returns typed response models to the API route.
7. The frontend renders those results in shipment lists, map views, action cards, decision logs, and simulation panels.

## Backend services and APIs

### Main route groups

- `routes_auth.py`
  - signup, login, Google login, token refresh, MFA verify/resend, logout, current user
- `routes_shipments.py`
  - shipment list and shipment detail
- `routes_monitoring.py`
  - monitoring summary and refresh
- `routes_alerts.py`
  - live alerts and decision log
- `routes_decisions.py`
  - evaluate shipment decision and simulate impact

### Health endpoint

- `GET /health`

### Authentication

- JWT access and refresh token flow
- Cookie-based session support
- Email OTP MFA support
- Local and Google-based sign-in paths

## Redis and background execution

Redis is part of the active request flow in this repository.

### Cache usage

- Shipment list responses are cached with Redis
- Monitoring summary responses are cached with Redis

### Queue usage

- Monitoring refresh pushes a job payload to a Redis list queue

### Background processing

- A Celery worker is included in the root Docker Compose stack
- The backend can optionally offload decision evaluation when `USE_BACKGROUND_EVALUATION=true`

### Relevant files

- `backend/app/services/redis_service.py`
- `backend/worker.py`
- `backend/app/worker.py`

## Persistence model

### Actively used

- SQLite is currently used for authentication and security-related persistence, including users, credentials, refresh tokens, and MFA challenges.

### Also present in the repo

- A SQLAlchemy/MySQL-style configuration layer exists in `backend/app/database.py` and related config fields. This appears to be additional scaffolding and is not the main active auth persistence path in the current runtime.

## Observability

The backend writes structured JSON logs including request and business context. Those logs are shipped through Promtail into Loki and viewed in Grafana.

### Logged fields include

- `timestamp`
- `log_level`
- `endpoint`
- `shipment_id`
- `request_id`
- `status_code`
- `duration_ms`

### Observability components

- `observability/promtail-config.yml`
- `observability/loki-config.yml`
- `observability/grafana/provisioning/`
- `observability/grafana/dashboards/logistics-logs.json`

## Running the full stack with Docker Compose

From the repository root:

```powershell
docker compose up --build
```

### Default ports

- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Grafana: `http://localhost:3000`
- Loki: `http://localhost:3100`
- Redis: `localhost:6379`

### Services started

- `backend`
- `frontend`
- `redis`
- `worker`
- `loki`
- `promtail`
- `grafana`

### Grafana access

- Username: `admin`
- Password: `admin`

## Local development

### Backend

From `backend/`:

```powershell
..\\venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --no-access-log
```

Install dependencies with:

```powershell
pip install -r requirements.txt
```

### Frontend

From `frontend/`:

```powershell
npm install
npm run dev
```

If the backend is not running at the default address, set:

```powershell
$env:VITE_API_BASE="http://127.0.0.1:8000/api"
```

## Key environment variables

### AI and signal providers

- `GROQ_API_KEY`
- `GROQ_MODEL`
- `OPENWEATHER_API_KEY`
- `OPENWEATHER_CITY`
- `OPENWEATHER_COUNTRY`

### Redis and async

- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `USE_BACKGROUND_EVALUATION`
- `SHIPMENTS_CACHE_TTL_SECONDS`
- `SUMMARY_CACHE_TTL_SECONDS`
- `REFRESH_QUEUE_KEY`

### Auth and security

- `JWT_SECRET_KEY`
- `PII_ENCRYPTION_KEY`
- `DATABASE_URL`
- `ALLOWED_ORIGINS`
- `GOOGLE_CLIENT_ID`
- `MFA_ENABLED`
- `MFA_SMTP_HOST`
- `MFA_SMTP_PORT`
- `MFA_SMTP_USERNAME`
- `MFA_SMTP_PASSWORD`
- `MFA_FROM_EMAIL`

### Logging

- `LOG_LEVEL`
- `LOG_FILE_PATH`
- `LOG_SERVICE_NAME`

## Security notes

- MFA is implemented as email OTP MFA.
- If SMTP is not configured, OTPs are generated but logged locally instead of being delivered by email.
- Several default secrets in configuration are development-friendly placeholders and should be replaced before any non-local deployment.
- Redis in the default Compose setup is appropriate for local development, not for an exposed production network.

## Frontend responsibilities

The frontend is primarily an operator-facing visualization and workflow layer. It:

- Manages auth and MFA state
- Polls shipment, alert, summary, and decision endpoints
- Displays map-based shipment tracking
- Shows recommended actions and decision reasoning
- Supports what-if impact simulation

Key files:

- `frontend/src/context/AuthContext.tsx`
- `frontend/src/hooks/useDashboardData.ts`
- `frontend/src/services/api.ts`
- `frontend/src/components/MapPanel.tsx`

## Troubleshooting

### Backend container keeps restarting

Check:

```powershell
docker logs logistics-ai-backend
```

### Redis logs

Follow Redis output with:

```powershell
docker compose logs -f redis
```

### Grafana shows no logs

Check that:

- `loki` is healthy
- `promtail` is running
- the backend is writing logs to `/app/logs/backend.log`

### MFA code not arriving by email

If SMTP is unset, the OTP is logged locally instead of being mailed. Inspect backend logs and configure the SMTP variables listed above.

## Additional documentation

- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)
- [Backend authentication quick start](backend/AUTH_QUICK_START.md)
- [Backend authentication details](backend/AUTHENTICATION.md)
- [Backend security setup](backend/SECURITY_SETUP.md)
- [Backend database notes](backend/DATABASE.md)

## Summary

This repository is organized around a practical intelligence pipeline for logistics operations:

- Data ingestion and enrichment create a live shipment state
- The ML layer scores operational risk and delay
- The agentic AI layer recommends actions
- The simulation layer estimates downstream impact
- Redis and Celery support responsive and asynchronous workflows
- Grafana Loki provides centralized visibility into backend behavior

That makes the project useful both as a working demo of logistics decision intelligence and as a base for extending into richer data pipelines, model serving, or more advanced agent orchestration.
