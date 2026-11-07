"""Comprueba que el OCR real lee cada placa del video en la zona que le corresponde."""
import os
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.core.config import OCR_CONFIDENCE_MIN, ROI_ENTRADA, ROI_SALIDA, VIDEO_PATH
from app.core.parking_logic import PLATE_PATTERN
from app.vision.plate_detector import PlateDetector

ESPERADO = [(4, "ABC-123", ROI_ENTRADA), (16, "XYZ-456", ROI_ENTRADA), (28, "ABC-123", ROI_SALIDA),
            (40, "K7R-352", ROI_ENTRADA), (52, "XYZ-456", ROI_SALIDA)]


def main():
    video = cv2.VideoCapture(VIDEO_PATH)
    detector = PlateDetector()
    fallos = 0
    for segundo, placa, roi in ESPERADO:
        leidas = []
        for extra in (0, 1):
            video.set(cv2.CAP_PROP_POS_FRAMES, (segundo + extra) * 30)
            _, frame = video.read()
            x1, y1, x2, y2 = roi
            leidas += detector.detect(frame[y1:y2, x1:x2])
        validas = [(t, round(c, 2)) for t, c in leidas if c >= OCR_CONFIDENCE_MIN and PLATE_PATTERN.match(t)]
        correcta = any(t == placa for t, _ in validas)
        fallos += not correcta
        print(f"{'OK ' if correcta else 'MAL'} {segundo:2d}s esperada={placa} leídas={leidas}")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
