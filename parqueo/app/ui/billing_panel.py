import customtkinter as ctk
from typing import List, Optional, Dict, Any

from app.database.models import Ticket


class BillingPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.configure(fg_color="#16213e")

        title = ctk.CTkLabel(self, text="Cobros y Vehículos",
                             font=("Helvetica", 16, "bold"),
                             text_color="#f39c12")
        title.pack(pady=(12, 4), padx=8, anchor="w")

        # Last charge section
        last_frame = ctk.CTkFrame(self, fg_color="#0f3460", corner_radius=8)
        last_frame.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(last_frame, text="Último Cobro",
                     font=("Helvetica", 13, "bold"),
                     text_color="#f39c12").pack(anchor="w", padx=8, pady=(6, 2))

        self._lbl_placa = ctk.CTkLabel(last_frame, text="—",
                                       font=("Courier", 20, "bold"),
                                       text_color="white")
        self._lbl_placa.pack(anchor="w", padx=8)

        self._lbl_tiempo = ctk.CTkLabel(last_frame, text="",
                                        font=("Helvetica", 12),
                                        text_color="#aaaaaa")
        self._lbl_tiempo.pack(anchor="w", padx=8)

        self._lbl_monto = ctk.CTkLabel(last_frame, text="",
                                       font=("Helvetica", 24, "bold"),
                                       text_color="#2ecc71")
        self._lbl_monto.pack(anchor="w", padx=8, pady=(0, 8))

        # Vehicles inside section
        ctk.CTkLabel(self, text="Vehículos Dentro",
                     font=("Helvetica", 13, "bold"),
                     text_color="#f39c12").pack(anchor="w", padx=8, pady=(8, 2))

        self._inside_scroll = ctk.CTkScrollableFrame(self, fg_color="#0f3460",
                                                     label_text="")
        self._inside_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def refresh(self, vehiculos_dentro: List[Ticket],
                ultimo_cobro: Optional[Dict[str, Any]]):
        # Update last charge
        if ultimo_cobro and ultimo_cobro.get("accion") == "SALIDA":
            self._lbl_placa.configure(text=ultimo_cobro.get("placa", "—"))
            mins = ultimo_cobro.get("minutos", 0)
            horas = mins // 60
            rest = mins % 60
            self._lbl_tiempo.configure(
                text=f"{horas}h {rest:02d}m estacionado")
            monto = ultimo_cobro.get("monto", 0.0) or 0.0
            self._lbl_monto.configure(text=f"S/ {monto:.2f}")

        # Rebuild vehicles-inside list
        for widget in self._inside_scroll.winfo_children():
            widget.destroy()

        if not vehiculos_dentro:
            ctk.CTkLabel(self._inside_scroll, text="Sin vehículos",
                         text_color="#555555",
                         font=("Helvetica", 12)).pack(pady=8)
            return

        for ticket in vehiculos_dentro:
            row = ctk.CTkFrame(self._inside_scroll, fg_color="#1a3a5c",
                               corner_radius=4)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=ticket.placa,
                         font=("Courier", 13, "bold"),
                         text_color="white",
                         anchor="w").pack(side="left", padx=8, pady=4)
            ctk.CTkLabel(row, text=f"desde {ticket.hora_entrada}",
                         font=("Helvetica", 11),
                         text_color="#aaaaaa",
                         anchor="w").pack(side="left", padx=4)
