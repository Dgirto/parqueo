import queue
import customtkinter as ctk

from app.core.config import VIDEO_PATH, FPS_TARGET
from app.core.theme import COLORS
from app.database.db_manager import DatabaseManager
from app.core.parking_logic import ParkingLogic
from app.vision.video_capture import VideoCaptureThread
from app.vision.plate_detector import PlateDetector
from app.vision.frame_processor import FrameProcessor
from app.ui.header_bar import HeaderBar
from app.ui.sidebar import Sidebar
from app.ui.video_panel import VideoPanel
from app.ui.detection_card import DetectionCard
from app.ui.active_vehicles import ActiveVehicles
from app.ui.activity_table import ActivityTable

MS_PER_FRAME = max(1, int(1000 / FPS_TARGET))


class MainWindow(ctk.CTk):
    def __init__(self, db_manager: DatabaseManager, parking_logic: ParkingLogic):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.db = db_manager
        self.logic = parking_logic
        self._after_jobs: list = []

        self.title("SmartPark — Control Center")
        self.geometry("1280x720")
        self.minsize(1280, 720)
        self.configure(fg_color=COLORS["bg_root"])

        # ── Queues ─────────────────────────────────────────────────
        self._frame_queue: queue.Queue = queue.Queue(maxsize=10)
        self._result_queue: queue.Queue = queue.Queue()

        # ── Vision pipeline ────────────────────────────────────────
        self._plate_detector = PlateDetector()
        self._frame_processor = FrameProcessor(
            self._plate_detector, self.logic, self._result_queue)

        # ── Layout ─────────────────────────────────────────────────
        self._build_layout()

        # ── Load initial data ──────────────────────────────────────
        self._initial_load()

        # ── Start capture thread ───────────────────────────────────
        self.capture_thread = VideoCaptureThread(VIDEO_PATH, self._frame_queue)
        self.capture_thread.start()

        # ── Start update loop ──────────────────────────────────────
        job = self.after(MS_PER_FRAME, self._update_loop)
        self._after_jobs.append(job)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Layout builder ─────────────────────────────────────────────

    def _build_layout(self):
        # Grid: col0=sidebar(200px), col1=video(flex), col2=right(320px)
        #       row0=header(56px), row1=main(flex), row2=table(180px)
        self.grid_columnconfigure(0, weight=0, minsize=200)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=0, minsize=320)
        self.grid_rowconfigure(0, weight=0, minsize=56)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0, minsize=180)

        # Sidebar — spans all 3 rows
        self.sidebar = Sidebar(self, on_navigate=self._on_navigate)
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="nsew")

        # Header — spans col 1 and 2
        self.header = HeaderBar(self)
        self.header.grid(row=0, column=1, columnspan=2, sticky="nsew")

        # Video panel
        self.video_panel = VideoPanel(self)
        self.video_panel.grid(row=1, column=1, sticky="nsew", padx=(8, 4), pady=8)

        # Right column: DetectionCard + ActiveVehicles stacked
        right_col = ctk.CTkFrame(self, fg_color="transparent")
        right_col.grid(row=1, column=2, sticky="nsew", padx=(4, 8), pady=8)
        right_col.grid_rowconfigure(0, weight=0)
        right_col.grid_rowconfigure(1, weight=1)
        right_col.grid_columnconfigure(0, weight=1)

        self.detection_card = DetectionCard(right_col,
                                            on_manual_exit=self._manual_exit)
        self.detection_card.grid(row=0, column=0, sticky="nsew", pady=(0, 6))

        self.active_vehicles = ActiveVehicles(right_col)
        self.active_vehicles.grid(row=1, column=0, sticky="nsew")

        # Activity table — spans col 1 and 2
        self.activity_table = ActivityTable(self)
        self.activity_table.grid(row=2, column=1, columnspan=2,
                                 sticky="nsew", padx=(8, 8), pady=(0, 8))

    # ── Initial data load ──────────────────────────────────────────

    def _initial_load(self):
        try:
            dentro = self.db.get_vehiculos_dentro()
            self.active_vehicles.refresh(dentro)

            historial = self.db.get_historial(limit=50)
            self.activity_table.refresh(historial)

            self._refresh_header_metrics()
        except Exception:
            pass

    # ── Main update loop ───────────────────────────────────────────

    def _update_loop(self):
        # Consume one video frame
        try:
            frame = self._frame_queue.get_nowait()
            self.video_panel.update_frame(frame)
            self._frame_processor.process(frame)
        except queue.Empty:
            pass

        # Consume all OCR results
        while True:
            try:
                result = self._result_queue.get_nowait()
                self._handle_result(result)
            except queue.Empty:
                break

        job = self.after(MS_PER_FRAME, self._update_loop)
        self._after_jobs.append(job)

    def _handle_result(self, result: dict):
        accion = result.get("accion", "")
        placa  = result.get("placa", "")
        hora   = result.get("hora", "")

        if accion not in ("ENTRADA", "SALIDA"):
            return

        # DetectionCard — determine hora_entrada for display
        if accion == "ENTRADA":
            hora_entrada = hora
        else:
            ticket = self.db.get_historial(limit=1)
            hora_entrada = ticket[0].hora_entrada if ticket else hora

        self.detection_card.update_detection(placa, hora_entrada, accion)

        # ActivityTable — get the saved ticket
        tickets = self.db.get_historial(limit=1)
        if accion == "SALIDA" and tickets:
            self.activity_table.prepend_row(tickets[0])
            self.activity_table.highlight_row(placa)
        elif accion == "ENTRADA":
            activos = self.db.get_vehiculos_dentro()
            ticket_activo = next((t for t in activos if t.placa == placa), None)
            if ticket_activo:
                self.activity_table.prepend_row(ticket_activo)

        # ActiveVehicles list
        dentro = self.db.get_vehiculos_dentro()
        self.active_vehicles.refresh(dentro)

        # Header metrics
        self._refresh_header_metrics()

    def _refresh_header_metrics(self):
        try:
            dentro_list = self.db.get_vehiculos_dentro()
            dentro_n = len(dentro_list)
            disponibles = max(0, 20 - dentro_n)
            historial = self.db.get_historial(limit=200)
            cobros_hoy = len(historial)
            total_hoy = sum(t.monto or 0.0 for t in historial)
            self.header.update_metrics(dentro_n, disponibles, cobros_hoy, total_hoy)
        except Exception:
            pass

    # ── Manual exit callback ───────────────────────────────────────

    def _manual_exit(self, placa: str):
        result = self.logic.procesar_placa(placa)
        if result["accion"] == "SALIDA":
            self._handle_result(result)

    # ── Navigation ─────────────────────────────────────────────────

    def _on_navigate(self, section: str):
        # Placeholder: in a full app each section would swap the center panel
        pass

    # ── Shutdown ───────────────────────────────────────────────────

    def _on_close(self):
        for job in self._after_jobs:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        if hasattr(self, "capture_thread"):
            self.capture_thread.stop()
            self.capture_thread.join(timeout=2.0)
        if hasattr(self, "db"):
            try:
                self.db.close()
            except Exception:
                pass
        self.destroy()
