import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '..', '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    DATABASE_URL = os.environ.get('DATABASE_URL', '')

