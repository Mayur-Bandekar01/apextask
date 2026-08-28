import os
from pathlib import Path
from dotenv import load_dotenv

# Load local .env if available
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Config:
    # Single-user Authentication
    APP_USERNAME = os.getenv('APP_USERNAME', 'mayur').strip()
    APP_PASSWORD = os.getenv('APP_PASSWORD', 'mayur123').strip()
    JWT_SECRET = os.getenv('JWT_SECRET', 'apex-task-super-secret-jwt-key-2026-xyz-production-99')
    JWT_EXPIRY_DAYS = int(os.getenv('JWT_EXPIRY_DAYS', 7))

    # MySQL Cloud / Local Credentials
    DB_HOST = os.getenv('MYSQL_HOST', os.getenv('DB_HOST', 'localhost'))
    DB_PORT = int(os.getenv('MYSQL_PORT', os.getenv('DB_PORT', 3306)))
    DB_USER = os.getenv('MYSQL_USER', os.getenv('DB_USER', 'root'))
    DB_PASSWORD = os.getenv('MYSQL_PASSWORD', os.getenv('DB_PASSWORD', ''))
    DB_NAME = os.getenv('MYSQL_DB', os.getenv('DB_NAME', 'todo_app'))
    DB_SSL_CA = os.getenv('MYSQL_SSL_CA', os.getenv('DB_SSL_CA', ''))

    SECRET_KEY = os.getenv('SECRET_KEY', 'apex-task-flask-secret-key-2026')
    PORT = int(os.getenv('PORT', 5000))
