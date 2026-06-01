import threading
import queue
import time

from app.core.config import OCR_INTERVAL_SECONDS, OCR_CONFIDENCE_MIN, ROI_ENTRADA, ROI_SALIDA
from app.vision.plate_detector import PlateDetector
from app.core.parking_logic import ParkingLogic


class OCRThread(threading.Thread):
    """Thread 2 — EasyOCR con detección por ROI direccional. Nunca toca BD."""

    def __init__(self, plate_detector: PlateDetector,
                 parking_logic: ParkingLogic,
                 ocr_queue: queue.Queue,
                 result_queue: queue.Queue):
        super().__init__(daemon=True)
        self.detector = plate_detector
        self.logic = parking_logic          # solo para validar_formato_placa
        self.ocr_queue = ocr_queue
        self.result_queue = result_queue    # emite dict {"placa": ..., "accion": ...}
        self._stop_event = threading.Event()
        self._last_ocr_time = 0.0
        self._recent_plates: set = set()    # debounce global

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

            # ── Buscar en ROI_ENTRADA ──────────────────────────────
            self._scan_roi(frame, ROI_ENTRADA, "ENTRADA")

            # ── Buscar en ROI_SALIDA ───────────────────────────────
            self._scan_roi(frame, ROI_SALIDA, "SALIDA")

    def _scan_roi(self, frame, roi: tuple, accion: str):
        x1, y1, x2, y2 = roi
        crop = frame[y1:y2, x1:x2]

        print(f"[OCR-SCAN] {accion}  roi={roi}  crop.shape={crop.shape}  crop.size={crop.size}")

        if crop.size == 0:
            print(f"[OCR-SCAN] {accion}  crop vacío, saltando")
            return

        try:
            candidates = self.detector.detect(crop)
        except Exception as e:
            print(f"[OCR-SCAN] {accion}  excepción en detect(): {e}")
            return

        print(f"[OCR-SCAN] {accion}  candidates={candidates}")

        for text, confidence in candidates:
            print(f"[OCR-FILTER] text={text!r}  conf={confidence:.2f}  "
                  f"min={OCR_CONFIDENCE_MIN}  válida={self.logic.validar_formato_placa(text)}  "
                  f"reciente={text in self._recent_plates}")
            if confidence < OCR_CONFIDENCE_MIN:
                continue
            if not self.logic.validar_formato_placa(text):
                continue
            if text in self._recent_plates:
                continue

            print(f"[OCR-EMIT] {accion}  placa={text}  conf={confidence:.2f}")
            self.result_queue.put({"placa": text, "accion": accion})
            self._recent_plates.add(text)
            if len(self._recent_plates) > 50:
                self._recent_plates.clear()

    def stop(self):
        self._stop_event.set()
