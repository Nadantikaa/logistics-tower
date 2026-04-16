# Logistics AI Backend

Run locally from `backend/`:

```powershell
..\\venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --no-access-log
```

Optional environment variables:

- `OPENWEATHER_API_KEY`
- `OPENWEATHER_CITY`
- `OPENWEATHER_COUNTRY`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `ALERT_CONFIDENCE_THRESHOLD`
- `LOG_LEVEL`
- `LOG_FILE_PATH`
- `LOG_SERVICE_NAME`

You can also store these in `backend/.env`.

For centralized logging, start the full stack from the repo root with Docker Compose. This provisions FastAPI JSON logs, Promtail, Loki, and Grafana with a preconfigured `Logistics Backend Logs` dashboard on port `3000`.
