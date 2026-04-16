import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ENV_FILE = BASE_DIR / ".env"


def _load_env_file() -> None:
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "logistics_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "logistics_password")
DB_NAME = os.getenv("DB_NAME", "logistics_db")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-min-32-chars")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Encryption Configuration
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "change-this-key-32-chars-min!!!!!")

# Weather API Configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENWEATHER_CITY = os.getenv("OPENWEATHER_CITY", "Chennai")
OPENWEATHER_COUNTRY = os.getenv("OPENWEATHER_COUNTRY", "IN")
OPENWEATHER_UNITS = "metric"

# Groq AI Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Background worker configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
USE_BACKGROUND_EVALUATION = os.getenv("USE_BACKGROUND_EVALUATION", "false").lower() == "true"

# Alert Configuration
ALERT_CONFIDENCE_THRESHOLD = int(os.getenv("ALERT_CONFIDENCE_THRESHOLD", "75"))

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-jwt-secret-change-me")
PII_ENCRYPTION_KEY = os.getenv("PII_ENCRYPTION_KEY", "dev-only-pii-secret-change-me")
DATABASE_URL = os.getenv("DATABASE_URL", str(DATA_DIR / "security.db"))
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",")
    if origin.strip()
]
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_TOKENINFO_URL = os.getenv(
    "GOOGLE_TOKENINFO_URL",
    "https://oauth2.googleapis.com/tokeninfo",
)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_TTL_MINUTES = int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "15"))
REFRESH_TOKEN_TTL_DAYS = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "7"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", "")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")
MFA_ENABLED = os.getenv("MFA_ENABLED", "true").lower() == "true"
MFA_OTP_TTL_MINUTES = int(os.getenv("MFA_OTP_TTL_MINUTES", "10"))
MFA_MAX_ATTEMPTS = int(os.getenv("MFA_MAX_ATTEMPTS", "5"))
MFA_SMTP_HOST = os.getenv("MFA_SMTP_HOST", "")
MFA_SMTP_PORT = int(os.getenv("MFA_SMTP_PORT", "587"))
MFA_SMTP_USERNAME = os.getenv("MFA_SMTP_USERNAME", "")
MFA_SMTP_PASSWORD = os.getenv("MFA_SMTP_PASSWORD", "")
MFA_SMTP_USE_TLS = os.getenv("MFA_SMTP_USE_TLS", "true").lower() == "true"
MFA_FROM_EMAIL = os.getenv("MFA_FROM_EMAIL", "no-reply@logistics-ai.local")
ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.getenv("ADMIN_EMAILS", "").split(",")
    if email.strip()
}
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", str(BASE_DIR / "logs" / "backend.log"))
LOG_SERVICE_NAME = os.getenv("LOG_SERVICE_NAME", "logistics-ai-backend")
