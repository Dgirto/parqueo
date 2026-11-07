import logging
import re
from typing import List, Tuple

import cv2
import numpy as np

try:
    import easyocr
    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False

logger = logging.getLogger(__name__)

CARACTERES_PLACA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"


def _hay_gpu() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


class PlateDetector:
    def __init__(self):
        if _EASYOCR_AVAILABLE:
            self.reader = easyocr.Reader(["es", "en"], gpu=_hay_gpu(), verbose=False)
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
            results = self.reader.readtext(preprocessed, detail=1, allowlist=CARACTERES_PLACA)
            plates = []
            for (_bbox, text, confidence) in results:
                cleaned = re.sub(r'[^A-Z0-9-]', '', text.upper())
                plates.append((cleaned, float(confidence)))
            return plates
        except Exception:
            logger.exception("Falló la lectura OCR")
            return []
