"""Une la captura, el OCR y la lógica de tickets, y publica lo que ocurre para la web."""
import asyncio
import logging
import queue
import threading
import time
from dataclasses import asdict
from typing import Callable, Dict, Optional, Set

import cv2

from app.core.config import OCR_CONFIDENCE_MIN
from app.core.parking_logic import ParkingLogic
from app.vision.ocr_thread import OCRThread
from app.vision.plate_detector import PlateDetector
from app.vision.video_capture import VideoCaptureThread

logger = logging.getLogger(__name__)


class Monitor:
    def __init__(self, logic: ParkingLogic, video_path: str,
                 crear_detector: Callable[[], PlateDetector] = PlateDetector):
        self.logic = logic
        self.db = logic.db
        self.video_path = video_path
        self._crear_detector = crear_detector

        self._display_queue: queue.Queue = queue.Queue(maxsize=4)
        self._ocr_queue: queue.Queue = queue.Queue(maxsize=1)
        self.result_queue: queue.Queue = queue.Queue()

        self._parar = threading.Event()
        self._captura: Optional[VideoCaptureThread] = None
        self._ocr: Optional[OCRThread] = None

        self._jpeg: Optional[bytes] = None
        self._secuencia = 0
        self._fps = 0.0
        self._ocr_estado = "cargando"

        self._suscriptores: Set[asyncio.Queue] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ── Ciclo de vida ──────────────────────────────────────────────

    def iniciar(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._captura = VideoCaptureThread(self.video_path, self._display_queue, self._ocr_queue)
        self._captura.start()
        threading.Thread(target=self._codificar_frames, daemon=True).start()
        threading.Thread(target=self._iniciar_ocr, daemon=True).start()
        threading.Thread(target=self._procesar_resultados, daemon=True).start()

    def detener(self) -> None:
        self._parar.set()
        if self._captura:
            self._captura.stop()
        if self._ocr:
            self._ocr.stop()

    def _iniciar_ocr(self) -> None:
        # EasyOCR tarda en cargar: el video arranca antes y la web muestra el estado.
        try:
            detector = self._crear_detector()
            if detector.reader is None:
                raise RuntimeError("EasyOCR no está instalado")
            self._ocr = OCRThread(detector, self.logic, self._ocr_queue, self.result_queue)
            self._ocr.start()
            self._ocr_estado = "listo"
        except Exception:
            logger.exception("No se pudo iniciar el OCR")
            self._ocr_estado = "error"
        self._publicar({"tipo": "estado", "estado": self.estado()})

    # ── Hilos de trabajo ───────────────────────────────────────────

    def _codificar_frames(self) -> None:
        contador, marca = 0, time.perf_counter()
        while not self._parar.is_set():
            try:
                frame = self._display_queue.get(timeout=0.5)
            except queue.Empty:
                self._fps = 0.0
                continue
            ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
            if ok:
                self._jpeg = jpg.tobytes()
                self._secuencia += 1
            contador += 1
            ahora = time.perf_counter()
            if ahora - marca >= 1.0:
                self._fps = round(contador / (ahora - marca), 1)
                contador, marca = 0, ahora

    def _procesar_resultados(self) -> None:
        while not self._parar.is_set():
            try:
                lectura = self.result_queue.get(timeout=0.25)
            except queue.Empty:
                continue
            self.procesar_lectura(lectura)

    def procesar_lectura(self, lectura: Dict) -> Dict:
        resultado = self.logic.procesar_placa(lectura["placa"], lectura["accion"])
        ticket = self.db.get_ticket_de_resultado(resultado)
        evento = {
            "tipo": "deteccion",
            "accion": resultado["accion"],
            "placa": resultado["placa"],
            "hora": resultado["hora"],
            "confianza": lectura.get("confianza"),
            "ticket": asdict(ticket) if ticket else None,
        }
        self._publicar(evento)
        return evento

    # ── Consultas para la API ──────────────────────────────────────

    def estado(self) -> Dict:
        return {
            "ocr": self._ocr_estado,
            "video": self._secuencia > 0,
            "fps": self._fps,
            "confianza_minima": OCR_CONFIDENCE_MIN,
        }

    def ultimo_frame(self):
        return self._secuencia, self._jpeg

    # ── Eventos en vivo ────────────────────────────────────────────

    def suscribir(self) -> asyncio.Queue:
        cola: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._suscriptores.add(cola)
        return cola

    def desuscribir(self, cola: asyncio.Queue) -> None:
        self._suscriptores.discard(cola)

    def publicar(self, evento: Dict) -> None:
        self._publicar(evento)

    def _publicar(self, evento: Dict) -> None:
        if self._loop is None or self._loop.is_closed():
            return

        def entregar():
            for cola in list(self._suscriptores):
                if cola.full():
                    cola.get_nowait()   # un cliente lento pierde lo más viejo
                cola.put_nowait(evento)

        self._loop.call_soon_threadsafe(entregar)
