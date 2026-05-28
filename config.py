import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'myvault-secret-key-change-in-production')

    # PostgreSQL on Render — falls back to SQLite locally
    DATABASE_URL = os.environ.get('DATABASE_URL', '')

    # Render gives postgres:// but SQLAlchemy needs postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///myvault.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # EmailJS
    EMAILJS_SERVICE_ID  = os.environ.get('EMAILJS_SERVICE_ID', '')
    EMAILJS_TEMPLATE_ID = os.environ.get('EMAILJS_TEMPLATE_ID', '')
    EMAILJS_PUBLIC_KEY  = os.environ.get('EMAILJS_PUBLIC_KEY', '')

    # Subscription reminder email template (separate template for reminders)
    EMAILJS_REMINDER_TEMPLATE_ID = os.environ.get('EMAILJS_REMINDER_TEMPLATE_ID', '')
