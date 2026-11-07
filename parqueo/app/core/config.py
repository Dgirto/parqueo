import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.getenv("PARQUEO_DB", os.path.join(BASE_DIR, "data", "parqueo.db"))
VIDEO_PATH = os.getenv("PARQUEO_VIDEO", os.path.join(BASE_DIR, "assets", "videos", "test.mp4"))
SCHEMA_PATH = os.path.join(BASE_DIR, "app", "database", "schema.sql")
WEB_DIST = os.path.join(BASE_DIR, "web", "dist")

HOST = os.getenv("PARQUEO_HOST", "127.0.0.1")
PORT = int(os.getenv("PARQUEO_PORT", "8100"))

TARIFA_ID_DEFAULT = 1
CAPACIDAD_DEFAULT = 20
OCR_INTERVAL_SECONDS = 0.5
OCR_CONFIDENCE_MIN = 0.6
PRECIO_HORA_DEFAULT = 5.00

# Zonas ROI para detección direccional (x1, y1, x2, y2)
# Coordenadas del frame ORIGINAL 1280x720: el recorte se hace antes de escalar.
FRAME_ANCHO = 1280
FRAME_ALTO = 720
# Se circula por la derecha: quien entra viene de frente por la mitad izquierda de la imagen.
ROI_ENTRADA = (0, 200, 640, 600)      # mitad izquierda
ROI_SALIDA = (640, 200, 1280, 600)    # mitad derecha
