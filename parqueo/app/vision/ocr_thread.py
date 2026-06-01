import threading
import queue
import time
import numpy as np

from app.core.config import OCR_INTERVAL_SECONDS, OCR_CONFIDENCE_MIN
from app.vision.plate_detector import PlateDetector
from app.core.parking_logic import ParkingLogic


class OCRThread(threading.Thread):
    """Thread 2 — corre EasyOCR en GPU sobre frames de ocr_queue."""

    def __init__(self, plate_detector: PlateDetector,
                 parking_logic: ParkingLogic,
                 ocr_queue: queue.Queue,
                 result_queue: queue.Queue):
        super().__init__(daemon=True)
        self.detector = plate_detector
        self.logic = parking_logic
        self.ocr_queue = ocr_queue
        self.result_queue = result_queue
        self._stop_event = threading.Event()
        self._processed_plates: set = set()
        self._last_ocr_time = 0.0

    def run(self):
        while not self._stop_event.is_set():
            try:
                frame = self.ocr_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            now = time.time()
            if now - self._last_ocr_time < OCR_INTERVAL_SECONDS:
                continue
            self._last_ocr_time = now

            try:
                candidates = self.detector.detect(frame)
            except Exception:
                continue

            for text, confidence in candidates:
                if confidence < OCR_CONFIDENCE_MIN:
                    continue
                if not self.logic.validar_formato_placa(text):
                    continue
                if text in self._processed_plates:
                    continue

                result = self.logic.procesar_placa(text)
                if result["accion"] in ("ENTRADA", "SALIDA"):
                    self.result_queue.put(result)
                    self._processed_plates.add(text)
                    if len(self._processed_plates) > 50:
                        self._processed_plates.clear()

    def stop(self):
        self._stop_event.set()
