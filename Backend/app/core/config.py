import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
os.makedirs(LOGS_DIR, exist_ok=True)

# API settings
API_HOST = "0.0.0.0"
API_PORT = 8000

# CORS settings
CORS_ORIGINS = [
    "http://localhost:3000",  # Frontend development server
    "http://127.0.0.1:3000",
]

# Personalities
PERSONALITIES = [
    {"id": "1", "name": "Friendly Advisor"},
    {"id": "2", "name": "Technical Expert"},
    {"id": "3", "name": "Creative Assistant"},
    {"id": "4", "name": "Motivational Coach"},
    {"id": "5", "name": "Analytical Thinker"},
    {"id": "6", "name": "Empathetic Listener"},
]
