import queue
import customtkinter as ctk

from app.core.config import VIDEO_PATH, FPS_TARGET
from app.database.db_manager import DatabaseManager
from app.core.parking_logic import ParkingLogic
from app.vision.video_capture import VideoCaptureThread
from app.vision.plate_detector import PlateDetector
from app.vision.frame_processor import FrameProcessor
from app.ui.video_panel import VideoPanel
from app.ui.registry_panel import RegistryPanel
from app.ui.billing_panel import BillingPanel


MS_PER_FRAME = max(1, int(1000 / FPS_TARGET))


class MainWindow(ctk.CTk):
    def __init__(self, db_manager: DatabaseManager, parking_logic: ParkingLogic):
        super().__init__()

        self.db = db_manager
        self.logic = parking_logic

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Sistema de Parqueo Inteligente")
        self.geometry("1280x720")
        self.minsize(960, 600)

        self._frame_queue: queue.Queue = queue.Queue(maxsize=10)
        self._result_queue: queue.Queue = queue.Queue()

        self._plate_detector = PlateDetector()
        self._frame_processor = FrameProcessor(
            self._plate_detector, self.logic, self._result_queue)

        self._build_layout()

        self._capture_thread = VideoCaptureThread(VIDEO_PATH, self._frame_queue)
        self._capture_thread.start()

        self.after(MS_PER_FRAME, self._update_loop)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self.video_panel = VideoPanel(self)
        self.video_panel.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)

        self.registry_panel = RegistryPanel(self)
        self.registry_panel.grid(row=0, column=1, sticky="nsew", padx=4, pady=8)

        self.billing_panel = BillingPanel(self)
        self.billing_panel.grid(row=0, column=2, sticky="nsew", padx=(4, 8), pady=8)

    def _update_loop(self):
        # Process one video frame
        try:
            frame = self._frame_queue.get_nowait()
            self.video_panel.update_frame(frame)
            self._frame_processor.process(frame)
        except queue.Empty:
            pass

        # Process all pending OCR results
        ultimo_cobro = None
        while True:
            try:
                result = self._result_queue.get_nowait()
                accion = result.get("accion", "")
                placa = result.get("placa", "")
                hora = result.get("hora", "")
                self.registry_panel.add_event(accion, placa, hora)
                if accion == "SALIDA":
                    ultimo_cobro = result
            except queue.Empty:
                break

        if ultimo_cobro is not None:
            vehiculos = self.db.get_vehiculos_dentro()
            self.billing_panel.refresh(vehiculos, ultimo_cobro)
        elif self._should_refresh_billing():
            vehiculos = self.db.get_vehiculos_dentro()
            self.billing_panel.refresh(vehiculos, None)

        self.after(MS_PER_FRAME, self._update_loop)

    _billing_tick = 0

    def _should_refresh_billing(self) -> bool:
        # Refresh billing panel every ~3 seconds to keep "dentro" list current
        self._billing_tick += 1
        if self._billing_tick >= FPS_TARGET * 3:
            self._billing_tick = 0
            return True
        return False

    def _on_close(self):
        self._capture_thread.stop()
        self.destroy()
