import cv2
import numpy as np
from typing import List, Tuple

try:
    import easyocr
    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False


class PlateDetector:
    def __init__(self):
        if _EASYOCR_AVAILABLE:
            self.reader = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
        else:
            self.reader = None

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Adaptive threshold to handle different lighting conditions
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        return cleaned

    def detect(self, frame: np.ndarray) -> List[Tuple[str, float]]:
        if self.reader is None:
            return []

        try:
            preprocessed = self.preprocess(frame)
            # Run OCR on the preprocessed frame
            results = self.reader.readtext(preprocessed, detail=1)
            plates = []
            for (_bbox, text, confidence) in results:
                cleaned = text.upper().replace(" ", "").replace(".", "")
                plates.append((cleaned, float(confidence)))
            return plates
        except Exception:
            return []
