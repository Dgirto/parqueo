import queue
import threading
import time
import customtkinter as ctk

from app.core.config import VIDEO_PATH, FPS_TARGET
from app.core.theme import COLORS
from app.database.db_manager import DatabaseManager
from app.core.parking_logic import ParkingLogic
from app.vision.video_capture import VideoCaptureThread
from app.vision.plate_detector import PlateDetector
from app.vision.ocr_thread import OCRThread
from app.ui.header_bar import HeaderBar
from app.ui.sidebar import Sidebar
from app.ui.video_panel import VideoPanel
from app.ui.detection_card import DetectionCard
from app.ui.active_vehicles import ActiveVehicles
from app.ui.activity_table import ActivityTable

MS_PER_FRAME = 33   # ~30fps para sincronizar con el video nativo

# ─────────────────────────────────────────────────────────────────────────────
# Flujo de datos (NINGUNA operación de BD corre en el hilo de Tkinter):
#
#  Thread 1 ─ VideoCaptureThread
#      cv2 → display_queue  (frames para UI)
#          → ocr_queue      (1/4 frames para OCR)
#
#  Thread 2 ─ OCRThread (GPU)
#      ocr_queue → detect placa → result_queue (str: placa)
#
#  Thread 3 ─ daemon por placa detectada
#      result_queue → procesar_placa() + DB reads → update_queue (dict UI)
#
#  Hilo Tkinter ─ _update_loop after(16ms)
#      display_queue → VideoPanel.update_frame()
#      update_queue  → actualiza widgets SOLO (cero BD aquí)
# ─────────────────────────────────────────────────────────────────────────────


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
        self._display_queue: queue.Queue = queue.Queue(maxsize=10)
        self._ocr_queue: queue.Queue = queue.Queue(maxsize=2)
        self._result_queue: queue.Queue = queue.Queue()    # str: placa detectada
        self._update_queue: queue.Queue = queue.Queue()    # dict: payload UI

        # Contadores de diagnóstico
        self._loop_count = 0
        self._loop_last_print = time.perf_counter()

        # ── Layout ─────────────────────────────────────────────────
        self._build_layout()

        # ── Thread 1: video capture (arranca inmediatamente) ───────
        self.capture_thread = VideoCaptureThread(
            VIDEO_PATH, self._display_queue, self._ocr_queue)
        self.capture_thread.start()

        # ── PlateDetector + OCRThread en background (EasyOCR es lento al init) ─
        threading.Thread(target=self._init_ocr, daemon=True).start()

        # ── Initial data ───────────────────────────────────────────
        threading.Thread(target=self._initial_load, daemon=True).start()

        # ── Hilo Tkinter: UI loop ──────────────────────────────────
        job = self.after(MS_PER_FRAME, self._update_loop)
        self._after_jobs.append(job)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Layout ─────────────────────────────────────────────────────

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=0, minsize=200)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=0, minsize=320)
        self.grid_rowconfigure(0, weight=0, minsize=56)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0, minsize=180)

        self.sidebar = Sidebar(self, on_navigate=self._on_navigate)
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="nsew")

        self.header = HeaderBar(self)
        self.header.grid(row=0, column=1, columnspan=2, sticky="nsew")

        self.video_panel = VideoPanel(self)
        self.video_panel.grid(row=1, column=1, sticky="nsew", padx=(8, 4), pady=8)

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

        self.activity_table = ActivityTable(self, on_clear=self._clear_bd)
        self.activity_table.grid(row=2, column=1, columnspan=2,
                                 sticky="nsew", padx=(8, 8), pady=(0, 8))

    # ── OCR init en background ────────────────────────────────────

    def _init_ocr(self):
        """Inicializa EasyOCR (lento) y arranca OCRThread en background."""
        print("[OCR] Cargando modelo EasyOCR…")
        t0 = time.perf_counter()
        plate_detector = PlateDetector()
        print(f"[OCR] Modelo listo en {time.perf_counter()-t0:.1f}s")

        self.ocr_thread = OCRThread(
            plate_detector, self.logic,
            self._ocr_queue, self._result_queue)
        self.ocr_thread.start()

    # ── Thread: carga inicial de datos ─────────────────────────────

    def _initial_load(self):
        """Corre en daemon thread; pone payload en update_queue para que UI lo aplique."""
        try:
            payload = self._build_refresh_payload()
            payload["tipo"] = "initial"
            self._update_queue.put(payload)
        except Exception:
            pass

    # ── Thread 3: procesar placa detectada (BD) ────────────────────

    def _procesar_en_background(self, placa: str):
        """Toda lógica de BD en daemon thread. Nunca toca widgets."""
        try:
            result = self.logic.procesar_placa(placa)
            accion = result.get("accion", "")

            if accion not in ("ENTRADA", "SALIDA"):
                return

            # Determinar hora_entrada para DetectionCard
            if accion == "ENTRADA":
                hora_entrada = result.get("hora", "")
            else:
                tickets = self.db.get_historial(limit=1)
                hora_entrada = tickets[0].hora_entrada if tickets else result.get("hora", "")

            # Ticket para la tabla
            nuevo_ticket = None
            if accion == "SALIDA":
                tickets = self.db.get_historial(limit=1)
                nuevo_ticket = tickets[0] if tickets else None
            elif accion == "ENTRADA":
                activos = self.db.get_vehiculos_dentro()
                nuevo_ticket = next((t for t in activos if t.placa == placa), None)

            # Payload completo para la UI (solo datos, cero widgets)
            payload = self._build_refresh_payload()
            payload.update({
                "tipo":         "deteccion",
                "accion":       accion,
                "placa":        placa,
                "hora_entrada": hora_entrada,
                "nuevo_ticket": nuevo_ticket,
            })
            self._update_queue.put(payload)

        except Exception:
            pass

    def _build_refresh_payload(self) -> dict:
        """Lee BD y construye el dict de estado — siempre en hilo background."""
        dentro   = self.db.get_vehiculos_dentro()
        historial = self.db.get_historial(limit=50)
        cobros   = len(historial)
        total    = sum(t.monto or 0.0 for t in historial)
        return {
            "dentro":    dentro,
            "historial": historial,
            "cobros":    cobros,
            "total":     total,
        }

    # ── Hilo Tkinter: _update_loop (solo renderiza, cero BD) ───────

    def _update_loop(self):
        # ── Diagnóstico: imprime 1 vez por segundo ─────────────────
        self._loop_count += 1
        now = time.perf_counter()
        if now - self._loop_last_print >= 1.0:
            dq = self._display_queue.qsize()
            print(f"[UI] loops/s={self._loop_count:3d}  "
                  f"display_q={dq}  "
                  f"result_q={self._result_queue.qsize()}  "
                  f"update_q={self._update_queue.qsize()}")
            self._loop_count = 0
            self._loop_last_print = now

        # Frame de video
        try:
            frame = self._display_queue.get_nowait()
            self.video_panel.update_frame(frame)
        except queue.Empty:
            pass

        # Placas detectadas → lanzar Thread 3 por cada una
        while True:
            try:
                placa = self._result_queue.get_nowait()
                threading.Thread(
                    target=self._procesar_en_background,
                    args=(placa,),
                    daemon=True,
                ).start()
            except queue.Empty:
                break

        # Payloads listos → actualizar widgets (cero BD aquí)
        while True:
            try:
                payload = self._update_queue.get_nowait()
                self._apply_payload(payload)
            except queue.Empty:
                break

        job = self.after(MS_PER_FRAME, self._update_loop)
        self._after_jobs.append(job)

    def _apply_payload(self, payload: dict):
        """Único lugar donde se tocan widgets. Solo lectura de payload, cero BD."""
        tipo = payload.get("tipo", "")

        # Refresca lista vehículos y métricas en todos los casos
        self.active_vehicles.refresh(payload.get("dentro", []))
        dentro_n    = len(payload.get("dentro", []))
        disponibles = max(0, 20 - dentro_n)
        self.header.update_metrics(
            dentro_n, disponibles,
            payload.get("cobros", 0),
            payload.get("total", 0.0),
        )

        if tipo == "initial":
            self.activity_table.refresh(payload.get("historial", []))
            return

        if tipo == "deteccion":
            accion       = payload.get("accion", "")
            placa        = payload.get("placa", "")
            hora_entrada = payload.get("hora_entrada", "")
            nuevo_ticket = payload.get("nuevo_ticket")

            self.detection_card.update_detection(placa, hora_entrada, accion)

            if nuevo_ticket is not None:
                self.activity_table.prepend_row(nuevo_ticket)
                if accion == "SALIDA":
                    self.activity_table.highlight_row(placa)

    # ── Manual exit ────────────────────────────────────────────────

    def _manual_exit(self, placa: str):
        threading.Thread(
            target=self._procesar_en_background,
            args=(placa,),
            daemon=True,
        ).start()

    # ── Limpiar BD ─────────────────────────────────────────────────

    def _clear_bd(self):
        def _do():
            self.db.clear_all_tickets()
            payload = self._build_refresh_payload()
            payload["tipo"] = "initial"
            self._update_queue.put(payload)

        threading.Thread(target=_do, daemon=True).start()

    # ── Navigation ─────────────────────────────────────────────────

    def _on_navigate(self, section: str):
        pass

    # ── Shutdown ───────────────────────────────────────────────────

    def _on_close(self):
        for job in self._after_jobs:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        if hasattr(self, "ocr_thread") and self.ocr_thread.is_alive():
            self.ocr_thread.stop()
            self.ocr_thread.join(timeout=2.0)
        if hasattr(self, "capture_thread"):
            self.capture_thread.stop()
            self.capture_thread.join(timeout=2.0)
        if hasattr(self, "db"):
            try:
                self.db.close()
            except Exception:
                pass
        self.destroy()
