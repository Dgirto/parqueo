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

        self._after_jobs = []
        self.current_image = None
        self._fps_counter = 0
        self._fps_display = 0.0
        self._frame_times: list[float] = []

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
        self._video_label = ctk.CTkLabel(self, text="",
                                         fg_color="#000000",
                                         corner_radius=0)
        self._video_label.pack(fill="both", expand=True)

        self.show_no_signal()
        self._start_blink()

    # ── public API ─────────────────────────────────────────────────

    def update_frame(self, frame: np.ndarray):
        import time
        now = time.time()
        self._frame_times.append(now)
        # Keep only the last 30 timestamps for FPS calculation
        self._frame_times = [t for t in self._frame_times if now - t <= 1.0]

        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)

            w = max(self._video_label.winfo_width(), 320)
            h = max(self._video_label.winfo_height(), 240)

            # Fit preserving aspect ratio
            img_w, img_h = pil_img.size
            scale = min(w / img_w, h / img_h)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)

            new_img = ctk.CTkImage(light_image=pil_img, size=(new_w, new_h))
            self._video_label.configure(image=new_img, text="")
            self.current_image = new_img   # prevent GC

            self._overlay_lbl.configure(
                text=f"{img_w}×{img_h}  ·  BGR/RGB  ·  OpenCV")
        except Exception:
            pass

    def update_fps(self, fps: float):
        self._fps_badge.configure(text=f"FPS: {fps:.0f}")

    def show_no_signal(self):
        self._video_label.configure(
            image=None,
            text="📷\n\nSIN SEÑAL",
            font=FONTS["title"],
            text_color=COLORS["text_secondary"],
        )
        self.current_image = None
        self._overlay_lbl.configure(text="Sin fuente de video")

    # ── internal ───────────────────────────────────────────────────

    def _start_blink(self):
        job = self.after(800, self._blink)
        self._after_jobs.append(job)

    def _blink(self):
        current = self._live_dot.cget("text_color")
        next_color = (COLORS["green"]
                      if current != COLORS["green"]
                      else COLORS["bg_card"])
        self._live_dot.configure(text_color=next_color)
        fps = len(self._frame_times)
        self._fps_badge.configure(text=f"FPS: {fps}")
        job = self.after(800, self._blink)
        self._after_jobs.append(job)
