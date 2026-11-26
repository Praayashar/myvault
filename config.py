import os
import sys
from dotenv import load_dotenv

load_dotenv()


def _require(name, hint):
    """Fail loudly at startup instead of running on an insecure default."""
    value = os.environ.get(name, '').strip()
    if not value:
        sys.stderr.write(
            f"\n[MyVault] FATAL: environment variable {name} is not set.\n"
            f"          {hint}\n\n"
        )
        raise RuntimeError(f"{name} is required")
    return value


class Config:
    # ---- Core -------------------------------------------------------------
    # No fallback on purpose. A guessable SECRET_KEY lets anyone forge a login
    # session, so the app must refuse to start without a real one.
    SECRET_KEY = _require(
        'SECRET_KEY',
        'Set it in Render > Environment. Generate one with: python -c "import secrets;print(secrets.token_urlsafe(48))"'
    )

    # ---- Database ---------------------------------------------------------
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    # Normalise the scheme, then name the driver explicitly.
    #
    # Supabase/Heroku hand out 'postgres://'. SQLAlchemy needs 'postgresql://'.
    # And from SQLAlchemy 2.1 a bare 'postgresql://' defaults to psycopg (v3),
    # not psycopg2 - so an unpinned upgrade makes the app die at startup with
    # "No module named 'psycopg'". Spelling out +psycopg2 keeps it working on
    # every SQLAlchemy version.
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    if DATABASE_URL.startswith('postgresql://'):
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL if DATABASE_URL else 'sqlite:///myvault.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'pool_size': 5,
        'max_overflow': 2,
        'connect_args': {'connect_timeout': 10} if DATABASE_URL else {}
    }

    # ---- Password vault encryption ---------------------------------------
    # Fernet key. Generate once with:
    #   python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"
    # KEEP YOUR OWN COPY. Lose this and every stored password is unreadable
    # forever - the encrypted database on its own is useless without it.
    VAULT_KEY = os.environ.get('VAULT_KEY', '').strip()

    # ---- Gemini (AI assistant) -------------------------------------------
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '').strip()
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash').strip()

    # ---- Cron endpoints (called by Google Apps Script) --------------------
    # Shared secret so only your Apps Script can trigger reminders/backup.
    CRON_SECRET = os.environ.get('CRON_SECRET', '').strip()

    # ---- Reminder lead times (days before the due date) -------------------
    LEAD_DAYS_SUBSCRIPTION = int(os.environ.get('LEAD_DAYS_SUBSCRIPTION', 3))
    LEAD_DAYS_EMI = int(os.environ.get('LEAD_DAYS_EMI', 3))
    LEAD_DAYS_HOME_TASK = int(os.environ.get('LEAD_DAYS_HOME_TASK', 3))
    LEAD_DAYS_INSURANCE = int(os.environ.get('LEAD_DAYS_INSURANCE', 7))
    LEAD_DAYS_VEHICLE = int(os.environ.get('LEAD_DAYS_VEHICLE', 7))
    LEAD_DAYS_DOCUMENT = int(os.environ.get('LEAD_DAYS_DOCUMENT', 7))
    LEAD_DAYS_INVESTMENT = int(os.environ.get('LEAD_DAYS_INVESTMENT', 7))

    # ---- Login protection -------------------------------------------------
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 8))
    LOGIN_LOCKOUT_MINUTES = int(os.environ.get('LOGIN_LOCKOUT_MINUTES', 15))

    # ---- Session cookie hardening ----------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Render serves over HTTPS; keep cookies off plain HTTP in production.
    SESSION_COOKIE_SECURE = bool(DATABASE_URL)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = bool(DATABASE_URL)
    WTF_CSRF_TIME_LIMIT = None  # tokens stay valid for the whole session

    # ---- EmailJS (manual "Email Report" button only) ----------------------
    # Automatic mail now goes out through Google Apps Script, not EmailJS.
    EMAILJS_SERVICE_ID = os.environ.get('EMAILJS_SERVICE_ID', '')
    EMAILJS_TEMPLATE_ID = os.environ.get('EMAILJS_TEMPLATE_ID', '')
    EMAILJS_PUBLIC_KEY = os.environ.get('EMAILJS_PUBLIC_KEY', '')
    EMAILJS_REMINDER_TEMPLATE_ID = os.environ.get('EMAILJS_REMINDER_TEMPLATE_ID', '')