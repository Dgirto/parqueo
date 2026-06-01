import threading
import queue
import time

from app.core.config import OCR_INTERVAL_SECONDS, OCR_CONFIDENCE_MIN, ROI_LECTURA
from app.vision.plate_detector import PlateDetector
from app.core.parking_logic import ParkingLogic

# Mínimo desplazamiento horizontal (px en frame completo) para confirmar dirección
MIN_DELTA_X = 10


class OCRThread(threading.Thread):
    """
    Thread 2 — EasyOCR con detección por dirección de movimiento.
    Nunca toca BD.

    Lógica:
    - Lee placas dentro de ROI_LECTURA (zona central donde el auto se detiene).
    - Compara posición X actual vs anterior para inferir dirección:
        x_actual < x_anterior  →  moviendo a la izquierda  →  ENTRADA
        x_actual > x_anterior  →  moviendo a la derecha    →  SALIDA
    - Solo emite cuando hay delta suficiente (evita falsos por jitter).
    """

    def __init__(self, plate_detector: PlateDetector,
                 parking_logic: ParkingLogic,
                 ocr_queue: queue.Queue,
                 result_queue: queue.Queue):
        super().__init__(daemon=True)
        self.detector = plate_detector
        self.logic = parking_logic
        self.ocr_queue = ocr_queue
        self.result_queue = result_queue    # emite dict {"placa": ..., "accion": ...}
        self._stop_event = threading.Event()
        self._last_ocr_time = 0.0
        # {placa: (last_cx, last_emit_time)} — rastreo por placa
        self._last_positions: dict = {}
        # debounce: no re-emitir la misma placa durante N segundos
        self._debounce_secs = 5.0

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

            x1, y1, x2, y2 = ROI_LECTURA
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            try:
                candidates = self.detector.detect(crop)
            except Exception:
                continue

            for text, confidence, cx_crop in candidates:
                if confidence < OCR_CONFIDENCE_MIN:
                    continue
                if not self.logic.validar_formato_placa(text):
                    continue

                # cx en coordenadas del frame completo
                cx = cx_crop + x1

                prev = self._last_positions.get(text)
                self._last_positions[text] = (cx, now)

                if prev is None:
                    # Primera vez — solo registrar posición, sin emitir
                    continue

                prev_cx, last_emit = prev
                delta = cx - prev_cx

                if abs(delta) < MIN_DELTA_X:
                    continue  # jitter, ignorar

                # Debounce: no re-emitir si ya se emitió hace poco
                if now - last_emit < self._debounce_secs:
                    continue

                accion = "ENTRADA" if delta < 0 else "SALIDA"
                self.result_queue.put({"placa": text, "accion": accion})
                # Actualizar tiempo de emisión para debounce
                self._last_positions[text] = (cx, now)

                print(f"[OCR] {text}  Δx={delta:+d}px  →  {accion}")

            # Limpiar posiciones antiguas (> 30s sin ver)
            stale = [p for p, (_, t) in self._last_positions.items()
                     if now - t > 30.0]
            for p in stale:
                del self._last_positions[p]

    def stop(self):
        self._stop_event.set()
