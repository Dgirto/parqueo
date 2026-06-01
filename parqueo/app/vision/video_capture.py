import threading
import queue
import cv2


class VideoCaptureThread(threading.Thread):
    """Thread 1 — captura frames a velocidad nativa y los encola para display."""

    def __init__(self, video_path: str,
                 display_queue: queue.Queue,
                 ocr_queue: queue.Queue):
        super().__init__(daemon=True)
        self.video_path = video_path
        self.display_queue = display_queue   # para el UI (máx 4 frames)
        self.ocr_queue = ocr_queue           # para el OCR thread (máx 2 frames)
        self._stop_event = threading.Event()

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)

        frame_count = 0
        while not self._stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_count = 0
                ret, frame = cap.read()
                if not ret:
                    break

            frame_count += 1

            # Display queue: todos los frames (UI los consume a ~60fps via after(16))
            if self.display_queue.qsize() < 4:
                self.display_queue.put(frame)

            # OCR queue: 1 de cada 4 frames para no saturar la GPU
            if frame_count % 4 == 0 and self.ocr_queue.qsize() < 2:
                self.ocr_queue.put(frame)

        cap.release()

    def stop(self):
        self._stop_event.set()
