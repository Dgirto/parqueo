import customtkinter as ctk
from datetime import datetime


class RegistryPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.configure(fg_color="#16213e")

        title = ctk.CTkLabel(self, text="Registro de Eventos",
                             font=("Helvetica", 16, "bold"),
                             text_color="#e94560")
        title.pack(pady=(12, 4), padx=8, anchor="w")

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="#0f3460",
                                              label_text="")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Column headers
        header = ctk.CTkFrame(self._scroll, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))
        for col, width in [("Acción", 80), ("Placa", 90), ("Hora", 130)]:
            ctk.CTkLabel(header, text=col, width=width,
                         font=("Helvetica", 12, "bold"),
                         text_color="#e94560",
                         anchor="w").pack(side="left", padx=4)

    def add_event(self, accion: str, placa: str, hora: str):
        color = "#2ecc71" if accion == "ENTRADA" else "#e74c3c"

        row = ctk.CTkFrame(self._scroll, fg_color="#1a3a5c", corner_radius=4)
        row.pack(fill="x", pady=2)

        ctk.CTkLabel(row, text=accion, width=80, font=("Helvetica", 12, "bold"),
                     text_color=color, anchor="w").pack(side="left", padx=6, pady=4)
        ctk.CTkLabel(row, text=placa, width=90, font=("Courier", 12),
                     text_color="white", anchor="w").pack(side="left", padx=4)
        ctk.CTkLabel(row, text=hora, width=130, font=("Helvetica", 11),
                     text_color="#aaaaaa", anchor="w").pack(side="left", padx=4)

        # Auto-scroll to the bottom
        self._scroll._parent_canvas.yview_moveto(1.0)
