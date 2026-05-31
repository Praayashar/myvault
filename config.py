import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'myvault-secret-key-change-in-production')

    # Get database URL
    DATABASE_URL = os.environ.get('DATABASE_URL', '')

    # Render gives postgres:// but SQLAlchemy needs postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    # Use PostgreSQL if available, else SQLite locally
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

    # EmailJS
    EMAILJS_SERVICE_ID = os.environ.get('EMAILJS_SERVICE_ID', '')
    EMAILJS_TEMPLATE_ID = os.environ.get('EMAILJS_TEMPLATE_ID', '')
    EMAILJS_PUBLIC_KEY = os.environ.get('EMAILJS_PUBLIC_KEY', '')
    EMAILJS_REMINDER_TEMPLATE_ID = os.environ.get('EMAILJS_REMINDER_TEMPLATE_ID', '')
