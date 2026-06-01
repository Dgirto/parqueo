import threading
import queue
import time
import cv2


class VideoCaptureThread(threading.Thread):
    """Thread 1 — captura a la velocidad nativa del video y distribuye frames."""

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

        # Leer FPS nativo del archivo (30.0 para test.mp4)
        native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_duration = 1.0 / native_fps

        frame_count = 0

        while not self._stop_event.is_set():
            t_start = time.perf_counter()

            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_count = 0
                ret, frame = cap.read()
                if not ret:
                    break

            frame_count += 1

            # ── Display queue: todos los frames ───────────────────
            if not self.display_queue.full():
                self.display_queue.put_nowait(frame)

            # ── OCR queue: 1 de cada 4 frames ─────────────────────
            if frame_count % 4 == 0 and not self.ocr_queue.full():
                self.ocr_queue.put_nowait(frame)

            # ── Sleep exacto para respetar el FPS nativo ──────────
            elapsed = time.perf_counter() - t_start
            sleep_time = frame_duration - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        cap.release()

    def stop(self):
        self._stop_event.set()
