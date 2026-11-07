"""Procesa el video en tiempo real y comprueba que cada lectura corresponde al auto en pantalla."""
import logging
import os
import queue
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.core.config import VIDEO_PATH
from app.core.parking_logic import ParkingLogic
from app.database.db_manager import DatabaseManager
from app.vision.ocr_thread import OCRThread
from app.vision.plate_detector import PlateDetector
from app.vision.video_capture import VideoCaptureThread

# (inicio, fin, placa, acción) de cada auto en el video de 60 s.
ESCENAS = [(0, 12, "ABC-123", "ENTRADA"), (12, 24, "XYZ-456", "ENTRADA"), (24, 36, "ABC-123", "SALIDA"),
           (36, 48, "K7R-352", "ENTRADA"), (48, 60, "XYZ-456", "SALIDA")]


class Registro(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lineas = []

    def emit(self, record):
        self.lineas.append(record.getMessage())


def main():
    vueltas = float(sys.argv[1]) if len(sys.argv) > 1 else 1.3
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db = DatabaseManager(os.path.join(tmp, "s.db"))
        db.initialize()
        registro = Registro()
        logger = logging.getLogger("app.vision.ocr_thread")
        logger.addHandler(registro)
        logger.setLevel(logging.INFO)

        vista, ocr, resultados = queue.Queue(maxsize=1), queue.Queue(maxsize=1), queue.Queue()
        detector = PlateDetector()   # se carga antes para que el video no avance sin OCR
        lector = OCRThread(detector, ParkingLogic(db), ocr, resultados)
        lector.start()
        captura = VideoCaptureThread(VIDEO_PATH, vista, ocr)
        captura.start()
        time.sleep(60 * vueltas)
        captura.stop()
        lector.stop()

    fallos = 0
    for linea in registro.lineas:
        accion, *campos = linea.split()
        datos = dict(c.split("=") for c in campos)
        pos = float(datos["segundo"]) % 60
        escena = next(e for e in ESCENAS if e[0] <= pos < e[1])
        bien = escena[2] == datos["placa"] and escena[3] == accion
        fallos += not bien
        print(f"{'OK ' if bien else 'MAL'} {accion:7} {datos['placa']} en el segundo {pos:4.1f}, "
              f"en pantalla {escena[2]} {escena[3]}, retraso {datos['latencia']} s")
    leidas = {(l.split()[0], l.split()[1].split("=")[1]) for l in registro.lineas}
    faltan = [e for e in ESCENAS if (e[3], e[2]) not in leidas]
    print(f"lecturas: {len(registro.lineas)}  sin leer: {[e[2] + ' ' + e[3] for e in faltan]}")
    sys.exit(1 if fallos or faltan else 0)


if __name__ == "__main__":
    main()
