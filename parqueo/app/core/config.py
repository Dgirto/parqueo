import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(BASE_DIR, "data", "parqueo.db")
VIDEO_PATH = r"C:/Users/Alumno-ETI/Desktop/parqueo/parqueo/assets/videos/test.mp4"
SCHEMA_PATH = os.path.join(BASE_DIR, "app", "database", "schema.sql")

TARIFA_ID_DEFAULT = 1
FPS_TARGET = 60
OCR_INTERVAL_SECONDS = 0.5
OCR_CONFIDENCE_MIN = 0.6
PRECIO_HORA_DEFAULT = 5.00

# Zonas ROI para detección direccional (x1, y1, x2, y2)
# Video 1280x720 escalado a 597x336 en el panel.
# Autos que ENTRAN vienen por la derecha, los que SALEN por la izquierda.
ROI_ENTRADA = (298, 0, 597, 336)   # mitad derecha del frame escalado
ROI_SALIDA  = (0,   0, 298, 336)   # mitad izquierda del frame escalado
