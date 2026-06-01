import time
import cv2
import numpy as np
from PIL import Image, ImageTk
import customtkinter as ctk
from app.core.theme import COLORS, FONTS, RADIUS


class VideoPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "#000000")
        kwargs.setdefault("corner_radius", RADIUS["card"])
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", COLORS["border_bright"])
        super().__init__(master, **kwargs)

        self.current_image = None   # mantiene referencia para evitar GC
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

        # Si el panel aún no tiene tamaño, leer directamente del widget
        w = self._panel_w or max(self._video_label.winfo_width(), 320)
        h = self._panel_h or max(self._video_label.winfo_height(), 240)

        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_h, img_w = frame.shape[:2]
            scale = min(w / img_w, h / img_h)
            new_w = max(1, int(img_w * scale))
            new_h = max(1, int(img_h * scale))

            # PIL resize + ImageTk directo (sin overhead de CTkImage)
            pil_resized = Image.fromarray(rgb).resize((new_w, new_h),
                                                      Image.BILINEAR)
            photo = ImageTk.PhotoImage(image=pil_resized)
            self._video_label.configure(image=photo)
            self.current_image = photo   # evitar GC

            self._overlay_lbl.configure(
                text=f"{img_w}×{img_h}  →  {new_w}×{new_h}  ·  OpenCV/PIL")
        except Exception:
            pass

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
