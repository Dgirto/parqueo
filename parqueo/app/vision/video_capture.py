import threading
import queue
import time
import cv2

TARGET_FPS = 30
_FRAME_INTERVAL = 1.0 / TARGET_FPS   # ~0.0333s entre frames


class VideoCaptureThread(threading.Thread):
    """Thread 1 — captura a ≤30fps reales y distribuye a display_queue y ocr_queue."""

    def __init__(self, video_path: str,
                 display_queue: queue.Queue,
                 ocr_queue: queue.Queue):
        super().__init__(daemon=True)
        self.video_path = video_path
        self.display_queue = display_queue
        self.ocr_queue = ocr_queue
        self._stop_event = threading.Event()

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)

        frame_count = 0
        last_frame_time = time.time()

        while not self._stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_count = 0
                ret, frame = cap.read()
                if not ret:
                    break

            frame_count += 1

            # ── Limitar a TARGET_FPS reales ────────────────────────
            now = time.time()
            elapsed = now - last_frame_time
            sleep_needed = _FRAME_INTERVAL - elapsed
            if sleep_needed > 0:
                time.sleep(sleep_needed)
            last_frame_time = time.time()

            # ── Display queue (maxsize=10): nunca bloquear ─────────
            if not self.display_queue.full():
                self.display_queue.put_nowait(frame)

            # ── OCR queue (maxsize=2): 1 de cada 4 frames ─────────
            if frame_count % 4 == 0 and not self.ocr_queue.full():
                self.ocr_queue.put_nowait(frame)

        cap.release()

    def stop(self):
        self._stop_event.set()
