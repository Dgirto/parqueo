import time
import queue
import numpy as np

from app.core.config import OCR_INTERVAL_SECONDS, OCR_CONFIDENCE_MIN
from app.vision.plate_detector import PlateDetector
from app.core.parking_logic import ParkingLogic


class FrameProcessor:
    def __init__(self, plate_detector: PlateDetector,
                 parking_logic: ParkingLogic,
                 result_queue: queue.Queue):
        self.detector = plate_detector
        self.logic = parking_logic
        self.result_queue = result_queue
        self._last_ocr_time = 0.0
        self._processed_plates: set = set()

    def process(self, frame: np.ndarray):
        now = time.time()
        if now - self._last_ocr_time < OCR_INTERVAL_SECONDS:
            return

        self._last_ocr_time = now
        candidates = self.detector.detect(frame)

        for text, confidence in candidates:
            if confidence < OCR_CONFIDENCE_MIN:
                continue
            if not self.logic.validar_formato_placa(text):
                continue
            # Debounce: avoid processing the same plate multiple times in a row
            if text in self._processed_plates:
                continue

            result = self.logic.procesar_placa(text)
            if result["accion"] in ("ENTRADA", "SALIDA"):
                self.result_queue.put(result)
                self._processed_plates.add(text)
                # Clear the debounce set after a while so re-entries are detected
                if len(self._processed_plates) > 50:
                    self._processed_plates.clear()
