import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(BASE_DIR, "data", "parqueo.db")
VIDEO_PATH = os.path.join(BASE_DIR, "assets", "videos", "test.mp4")
SCHEMA_PATH = os.path.join(BASE_DIR, "app", "database", "schema.sql")

TARIFA_ID_DEFAULT = 1
FPS_TARGET = 60
OCR_INTERVAL_SECONDS = 0.5
OCR_CONFIDENCE_MIN = 0.6
PRECIO_HORA_DEFAULT = 5.00
