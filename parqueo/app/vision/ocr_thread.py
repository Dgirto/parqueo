import logging
import queue
import threading
import time

import cv2
import numpy as np

from app.core.config import OCR_CONFIDENCE_MIN, OCR_INTERVAL_SECONDS, ROI_ENTRADA, ROI_SALIDA
from app.core.parking_logic import ParkingLogic, normalizar_placa
from app.vision.plate_detector import PlateDetector

logger = logging.getLogger(__name__)

# Parte de la zona que debe cambiar frente al fondo para gastar una lectura de OCR.
PRESENCIA_MINIMA = 0.04


class DetectorPresencia:
    """Compara la zona con su fondo aprendido para saber si hay un vehículo."""

    def __init__(self):
        self._fondo = None

    def hay_vehiculo(self, recorte: np.ndarray) -> bool:
        reducido = cv2.resize(recorte, (160, 100), interpolation=cv2.INTER_AREA)
        gris = cv2.GaussianBlur(cv2.cvtColor(reducido, cv2.COLOR_BGR2GRAY), (5, 5), 0).astype(np.float32)
        if self._fondo is None:
            self._fondo = gris
            return True
        cambio = np.abs(gris - self._fondo) > 22
        presente = float(cambio.mean()) > PRESENCIA_MINIMA
        # El fondo solo aprende donde no cambió, así un auto detenido no se vuelve fondo.
        self._fondo = np.where(cambio, self._fondo, self._fondo * 0.9 + gris * 0.1)
        return presente


class OCRThread(threading.Thread):
    """Thread 2: EasyOCR con detección por ROI direccional. Nunca toca la BD."""

    def __init__(self, plate_detector: PlateDetector,
                 parking_logic: ParkingLogic,
                 ocr_queue: queue.Queue,
                 result_queue: queue.Queue):
        super().__init__(daemon=True)
        self.detector = plate_detector
        self.logic = parking_logic          # solo para validar_formato_placa
        self.ocr_queue = ocr_queue          # (frame, instante de captura, segundo del video)
        self.result_queue = result_queue    # emite dict {"placa", "accion", "confianza", ...}
        self._stop_event = threading.Event()
        self._last_ocr_time = 0.0
        self._recent_plates: dict = {}      # {placa: last_emit_timestamp}
        self._debounce_secs = 15.0
        self._presencia = {"ENTRADA": DetectorPresencia(), "SALIDA": DetectorPresencia()}

    def run(self):
        while not self._stop_event.is_set():
            try:
                frame, capturado, segundo = self.ocr_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            now = time.time()
            if now - self._last_ocr_time < OCR_INTERVAL_SECONDS:
                continue
            self._last_ocr_time = now

            self._scan_roi(frame, ROI_ENTRADA, "ENTRADA", capturado, segundo)
            self._scan_roi(frame, ROI_SALIDA, "SALIDA", capturado, segundo)

    def _scan_roi(self, frame, roi: tuple, accion: str, capturado: float, segundo: float):
        x1, y1, x2, y2 = roi
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0 or not self._presencia[accion].hay_vehiculo(crop):
            return

        try:
            candidates = self.detector.detect(crop)
        except Exception:
            logger.exception("Falló la detección en %s", accion)
            return

        now = time.time()
        for text, confidence in candidates:
            if confidence < OCR_CONFIDENCE_MIN:
                continue
            if not self.logic.validar_formato_placa(text):
                continue
            text = normalizar_placa(text)
            if (now - self._recent_plates.get(text, 0.0)) < self._debounce_secs:
                continue

            latencia = time.monotonic() - capturado
            logger.info("%s placa=%s confianza=%.2f segundo=%.1f latencia=%.1f",
                        accion, text, confidence, segundo, latencia)
            self.result_queue.put({"placa": text, "accion": accion, "confianza": confidence,
                                   "latencia": round(latencia, 2)})
            self._recent_plates[text] = now

    def stop(self):
        self._stop_event.set()
