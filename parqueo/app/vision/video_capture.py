import threading
import queue
import cv2


class VideoCaptureThread(threading.Thread):
    def __init__(self, video_path: str, frame_queue: queue.Queue):
        super().__init__(daemon=True)
        self.video_path = video_path
        self.frame_queue = frame_queue
        self._stop_event = threading.Event()

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            # Fall back to webcam index 0 if the file is unavailable
            cap = cv2.VideoCapture(0)

        frame_count = 0
        while not self._stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                # Restart video from the beginning
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_count = 0
                ret, frame = cap.read()
                if not ret:
                    break

            frame_count += 1
            # Send 1 of every 3 frames to keep the UI thread responsive
            if frame_count % 3 != 0:
                continue

            # Keep the queue shallow to avoid memory bloat
            if self.frame_queue.qsize() < 5:
                self.frame_queue.put(frame)

        cap.release()

    def stop(self):
        self._stop_event.set()
