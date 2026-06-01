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
# El video es 1280x720. Autos que ENTRAN vienen por la derecha,
# los que SALEN vienen por la izquierda.
ROI_ENTRADA = (640, 200, 1280, 530)   # mitad derecha del frame
ROI_SALIDA  = (0,   200,  640, 530)   # mitad izquierda del frame
