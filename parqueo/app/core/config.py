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
# Coordenadas del frame ORIGINAL 1280x720 — el crop en ocr_thread se hace
# antes de cualquier escalado.
ROI_ENTRADA = (640, 200, 1280, 600)   # mitad derecha, frame original 1280x720
ROI_SALIDA  = (0,   200,  640, 600)   # mitad izquierda, frame original 1280x720
