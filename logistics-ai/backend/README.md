# Logistics AI Backend

Run locally from `backend/`:

```powershell
..\\venv\\Scripts\\python.exe -m uvicorn app.main:app --reload
```

Optional environment variables:

- `OPENWEATHER_API_KEY`
- `OPENWEATHER_CITY`
- `OPENWEATHER_COUNTRY`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `ALERT_CONFIDENCE_THRESHOLD`

You can also store these in `backend/.env`.
