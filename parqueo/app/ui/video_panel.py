import time
import cv2
import numpy as np
from PIL import Image
import customtkinter as ctk
from app.core.theme import COLORS, FONTS, RADIUS


class VideoPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "#000000")
        kwargs.setdefault("corner_radius", RADIUS["card"])
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", COLORS["border_bright"])
        super().__init__(master, **kwargs)

        # Fuerza expansión del frame dentro de su celda grid
        self.grid_propagate(True)

        self.current_image = None
        self._frame_times: list[float] = []
        self._panel_w = 640
        self._panel_h = 480

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

        # ── Video label (ocupa todo el espacio restante) ───────────
        self._video_label = ctk.CTkLabel(self, text="",
                                         fg_color="#000000",
                                         corner_radius=0)
        self._video_label.pack(fill="both", expand=True)

        # Seguir el tamaño real del panel cuando cambia
        self.bind("<Configure>", self._on_resize)

        self.show_no_signal()
        self.after(800, self._blink)

    # ── Resize handler ─────────────────────────────────────────────

    def _on_resize(self, event):
        # Descontar top bar (32) y bottom bar (28)
        self._panel_w = max(event.width, 320)
        self._panel_h = max(event.height - 60, 240)

    # ── public API ─────────────────────────────────────────────────

    def update_frame(self, frame: np.ndarray):
        now = time.time()
        self._frame_times = [t for t in self._frame_times if now - t <= 1.0]
        self._frame_times.append(now)

        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)

            img_w, img_h = pil_img.size
            scale = min(self._panel_w / img_w, self._panel_h / img_h)
            new_w = max(1, int(img_w * scale))
            new_h = max(1, int(img_h * scale))

            # Resize en PIL (más rápido que CTkImage interno)
            pil_resized = pil_img.resize((new_w, new_h), Image.BILINEAR)
            new_img = ctk.CTkImage(light_image=pil_resized, size=(new_w, new_h))
            self._video_label.configure(image=new_img, text="")
            self.current_image = new_img   # evitar GC

            self._overlay_lbl.configure(
                text=f"{img_w}×{img_h}  →  {new_w}×{new_h}  ·  OpenCV/PIL")
        except Exception:
            pass

    def show_no_signal(self):
        self._video_label.configure(
            image=None,
            text="📷\n\nSIN SEÑAL",
            font=FONTS["title"],
            text_color=COLORS["text_secondary"],
        )
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
