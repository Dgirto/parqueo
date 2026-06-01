import time
import cv2
import numpy as np
from PIL import Image, ImageTk
import customtkinter as ctk
from app.core.theme import COLORS, FONTS, RADIUS
from app.core.config import ROI_ENTRADA, ROI_SALIDA


class VideoPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "#000000")
        kwargs.setdefault("corner_radius", RADIUS["card"])
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", COLORS["border_bright"])
        super().__init__(master, **kwargs)

        self._photo = None          # referencia anti-GC (doble: self + label.image)
        self._frame_times: list[float] = []
        self._panel_w = 0
        self._panel_h = 0

        # ── Top bar ────────────────────────────────────────────────
        top_bar = ctk.CTkFrame(self, height=32, corner_radius=0,
                               fg_color="#0A0A0F")
        top_bar.pack(fill="x", side="top")
        top_bar.pack_propagate(False)

        self._live_dot = ctk.CTkLabel(top_bar, text="●",
                                      font=FONTS["small"],
                                      text_color=COLORS["green"])
        self._live_dot.pack(side="left", padx=(10, 2))
        ctk.CTkLabel(top_bar, text="EN VIVO  ·  Cámara 01 — Entrada Principal",
                     font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self._fps_badge = ctk.CTkLabel(top_bar, text="FPS: --",
                                       font=FONTS["small"],
                                       text_color=COLORS["cyan"])
        self._fps_badge.pack(side="right", padx=10)

        # ── Bottom overlay ─────────────────────────────────────────
        bottom_bar = ctk.CTkFrame(self, height=28, corner_radius=0,
                                  fg_color="#0D0D14")
        bottom_bar.pack(fill="x", side="bottom")
        bottom_bar.pack_propagate(False)
        self._overlay_lbl = ctk.CTkLabel(bottom_bar, text="—",
                                         font=FONTS["small"],
                                         text_color=COLORS["text_secondary"])
        self._overlay_lbl.pack(side="left", padx=10)

        # ── Video label ────────────────────────────────────────────
        # Usamos tk.Label (no CTkLabel) para aceptar ImageTk.PhotoImage
        # directamente — evita la capa de conversión de CTkImage
        import tkinter as tk
        self._video_label = tk.Label(self, bg="#000000", bd=0,
                                     highlightthickness=0)
        self._video_label.pack(fill="both", expand=True)

        # Actualizar dimensiones cuando el panel cambia de tamaño
        self.bind("<Configure>", self._on_resize)

        self.show_no_signal()
        self.after(800, self._blink)

    # ── Resize ─────────────────────────────────────────────────────

    def _on_resize(self, event):
        self._panel_w = max(event.width, 160)
        self._panel_h = max(event.height - 60, 120)   # descontar top+bottom bar

    # ── public API ─────────────────────────────────────────────────

    def update_frame(self, frame: np.ndarray):
        now = time.time()
        self._frame_times = [t for t in self._frame_times if now - t <= 1.0]
        self._frame_times.append(now)

        # Tamaño real del label (con fallback si aún no ha sido dibujado)
        w = self._video_label.winfo_width()
        h = self._video_label.winfo_height()
        if w < 10:
            w = self._panel_w or 640
        if h < 10:
            h = self._panel_h or 480

        try:
            img_h_orig, img_w_orig = frame.shape[:2]

            # 0. Dibujar overlay de zonas ROI (semitransparente)
            frame = self._draw_roi_overlay(frame)

            # 1. BGR → RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 2. Redimensionar con cv2 (más rápido que PIL para resize)
            scale = min(w / img_w_orig, h / img_h_orig)
            new_w = max(1, int(img_w_orig * scale))
            new_h = max(1, int(img_h_orig * scale))
            rgb_resized = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

            # 3. numpy array → PIL Image
            pil_img = Image.fromarray(rgb_resized)

            # 4. PIL Image → ImageTk.PhotoImage
            photo = ImageTk.PhotoImage(pil_img)

            # 5. Guardar referencia (CRÍTICO: evita que el GC destruya la imagen)
            self._photo = photo

            # 6. Asignar al label (doble referencia anti-GC)
            self._video_label.configure(image=self._photo)
            self._video_label.image = self._photo

            self._overlay_lbl.configure(
                text=f"{img_w_orig}×{img_h_orig}  →  {new_w}×{new_h}  ·  OpenCV/PIL")
        except Exception:
            pass

    # ── ROI overlay ────────────────────────────────────────────────

    @staticmethod
    def _draw_roi_overlay(frame: np.ndarray) -> np.ndarray:
        """
        Escala las coordenadas ROI (definidas en el frame reducido 597x336)
        al tamaño real del frame recibido y dibuja el overlay semitransparente.
        """
        fh, fw = frame.shape[:2]
        roi_w, roi_h = 1280, 720   # ROI definidas en coordenadas del frame original

        def scale(roi):
            x1, y1, x2, y2 = roi
            return (
                int(x1 * fw / roi_w), int(y1 * fh / roi_h),
                int(x2 * fw / roi_w), int(y2 * fh / roi_h),
            )

        e = scale(ROI_ENTRADA)
        s = scale(ROI_SALIDA)

        overlay = frame.copy()
        cv2.rectangle(overlay, (e[0], e[1]), (e[2], e[3]), (0, 200, 80), -1)
        cv2.rectangle(overlay, (s[0], s[1]), (s[2], s[3]), (0, 60, 220), -1)
        frame_out = cv2.addWeighted(overlay, 0.18, frame, 0.82, 0)

        cv2.rectangle(frame_out, (e[0], e[1]), (e[2], e[3]), (0, 210, 90), 2)
        cv2.putText(frame_out, "ENTRADA", (e[0] + 8, e[1] + 26),
                    cv2.FONT_HERSHEY_DUPLEX, 0.75, (0, 230, 100), 2, cv2.LINE_AA)

        cv2.rectangle(frame_out, (s[0], s[1]), (s[2], s[3]), (60, 60, 230), 2)
        cv2.putText(frame_out, "SALIDA", (s[0] + 8, s[1] + 26),
                    cv2.FONT_HERSHEY_DUPLEX, 0.75, (80, 80, 245), 2, cv2.LINE_AA)

        return frame_out

    def show_no_signal(self):
        self._video_label.configure(image="", text="📷  SIN SEÑAL")
        self.current_image = None
        self._overlay_lbl.configure(text="Sin fuente de video")

    # ── Blink ──────────────────────────────────────────────────────

    def _blink(self):
        current = self._live_dot.cget("text_color")
        self._live_dot.configure(
            text_color=COLORS["green"] if current != COLORS["green"]
            else COLORS["bg_card"])
        self._fps_badge.configure(text=f"FPS: {len(self._frame_times)}")
        self.after(800, self._blink)
