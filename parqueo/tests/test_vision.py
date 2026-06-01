import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_plate_detector_preprocess():
    """Preprocessing must return a single-channel binary image of the same HxW."""
    from app.vision.plate_detector import PlateDetector
    detector = PlateDetector()
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    result = detector.preprocess(frame)
    assert result.shape == (480, 640)
    assert result.dtype == np.uint8


def test_plate_detector_detect_returns_list():
    """detect() must return a list even when no plates are found."""
    from app.vision.plate_detector import PlateDetector
    detector = PlateDetector()
    blank = np.zeros((100, 200, 3), dtype=np.uint8)
    results = detector.detect(blank)
    assert isinstance(results, list)


def test_video_capture_thread_init():
    """VideoCaptureThread must be initializable without starting."""
    import queue
    from app.vision.video_capture import VideoCaptureThread
    q = queue.Queue()
    thread = VideoCaptureThread("nonexistent.mp4", q)
    assert not thread.is_alive()
    assert thread.daemon is True


def test_frame_processor_rate_limit():
    """FrameProcessor must not call OCR twice within OCR_INTERVAL_SECONDS."""
    import queue
    import time
    from unittest.mock import MagicMock, patch
    from app.vision.frame_processor import FrameProcessor

    mock_detector = MagicMock()
    mock_detector.detect.return_value = []
    mock_logic = MagicMock()
    result_q = queue.Queue()

    processor = FrameProcessor(mock_detector, mock_logic, result_q)
    frame = np.zeros((100, 200, 3), dtype=np.uint8)

    processor.process(frame)
    processor.process(frame)  # second call within interval — should skip OCR

    assert mock_detector.detect.call_count == 1
