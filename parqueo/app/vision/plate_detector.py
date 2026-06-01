import re
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
            self.reader = easyocr.Reader(["es", "en"], gpu=True, verbose=False)
        else:
            self.reader = None

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    def detect(self, frame: np.ndarray) -> List[Tuple[str, float]]:
        if self.reader is None:
            return []

        try:
            preprocessed = self.preprocess(frame)
            results = self.reader.readtext(preprocessed, detail=1)
            print(f"[OCR-RAW] readtext devolvió {len(results)} resultado(s): {results}")
            plates = []
            for (_bbox, text, confidence) in results:
                cleaned = re.sub(r'[^A-Z0-9-]', '', text.upper())
                plates.append((cleaned, float(confidence)))
            return plates
        except Exception as e:
            print(f"[OCR-RAW] excepción en detect(): {e}")
            return []
