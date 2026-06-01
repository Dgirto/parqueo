import customtkinter as ctk
from PIL import Image, ImageTk
import numpy as np
import cv2


class VideoPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.configure(fg_color="#1a1a2e")

        self._label = ctk.CTkLabel(self, text="Esperando video...",
                                   text_color="#aaaaaa", font=("Helvetica", 14))
        self._label.pack(expand=True, fill="both", padx=4, pady=4)
        self._photo = None

    def update_frame(self, frame: np.ndarray):
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)

            # Fit within panel while preserving aspect ratio
            panel_w = self.winfo_width() or 640
            panel_h = self.winfo_height() or 480
            img.thumbnail((panel_w, panel_h), Image.LANCZOS)

            self._photo = ImageTk.PhotoImage(img)
            self._label.configure(image=self._photo, text="")
        except Exception:
            pass
