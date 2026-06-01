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

# Zona ROI de lectura (x1, y1, x2, y2) en coordenadas del frame original 1280x720.
# Zona central donde el auto se detiene frente a la barrera.
# La dirección se infiere comparando la posición X entre frames consecutivos:
#   x_actual < x_anterior  →  moviendo izquierda  →  ENTRADA
#   x_actual > x_anterior  →  moviendo derecha    →  SALIDA
ROI_LECTURA = (200, 280, 800, 480)
