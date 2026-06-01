from datetime import datetime
import customtkinter as ctk
from app.core.theme import COLORS, FONTS, RADIUS
from app.core.config import PRECIO_HORA_DEFAULT


_TIPO_ICON = {"MOTO": "🏍", "AUTO": "🚗", "CAMION": "🚛"}


class ActiveVehicles(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_card"])
        kwargs.setdefault("corner_radius", RADIUS["card"])
        super().__init__(master, **kwargs)

        self._after_jobs = []
        self._rows: list[dict] = []   # [{placa, hora_entrada, tipo, widgets}]

        # ── Header ─────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(hdr, text="VEHÍCULOS DENTRO",
                     font=FONTS["title"],
                     text_color=COLORS["text_primary"]).pack(side="left")

        self._count_badge = ctk.CTkLabel(hdr, text=" 0 ",
                                         font=FONTS["body_bold"],
                                         fg_color="#0D2A33",
                                         text_color=COLORS["cyan"],
                                         corner_radius=RADIUS["badge"])
        self._count_badge.pack(side="right")

        # ── Scroll area ────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                              label_text="")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ── public API ─────────────────────────────────────────────────

    def refresh(self, vehiculos: list):
        for w in self._scroll.winfo_children():
            w.destroy()
        self._rows.clear()

        for i, ticket in enumerate(vehiculos):
            self._add_row(ticket.placa, ticket.hora_entrada,
                          getattr(ticket, "tipo", "AUTO"), i)

        self._count_badge.configure(text=f" {len(vehiculos)} ")
        self._schedule_time_refresh()

    def add_vehicle(self, placa: str, hora_entrada: str, tipo: str = "AUTO"):
        idx = len(self._rows)
        self._add_row(placa, hora_entrada, tipo, idx)
        count = len(self._rows)
        self._count_badge.configure(text=f" {count} ")

    def remove_vehicle(self, placa: str):
        to_remove = [r for r in self._rows if r["placa"] == placa]
        for row in to_remove:
            row["frame"].destroy()
            self._rows.remove(row)
        self._count_badge.configure(text=f" {len(self._rows)} ")

    # ── internal ───────────────────────────────────────────────────

    def _add_row(self, placa: str, hora_entrada: str, tipo: str, idx: int):
        bg = COLORS["bg_row_even"] if idx % 2 == 0 else COLORS["bg_row_odd"]
        icon = _TIPO_ICON.get(tipo.upper(), "🚗")

        frame = ctk.CTkFrame(self._scroll, fg_color=bg,
                             corner_radius=8, height=40)
        frame.pack(fill="x", pady=2)
        frame.pack_propagate(False)

        # Hover bindings
        frame.bind("<Enter>", lambda e, f=frame: f.configure(fg_color=COLORS["bg_row_hover"]))
        frame.bind("<Leave>", lambda e, f=frame, b=bg: f.configure(fg_color=b))

        ctk.CTkLabel(frame, text=icon, font=FONTS["body"],
                     text_color=COLORS["text_primary"]).pack(side="left", padx=(8, 4))

        ctk.CTkLabel(frame, text=placa, font=FONTS["body_bold"],
                     text_color=COLORS["text_primary"]).pack(side="left", padx=(0, 8))

        time_lbl = ctk.CTkLabel(frame, text=self._elapsed(hora_entrada),
                                font=FONTS["mono"],
                                text_color=COLORS["text_secondary"])
        time_lbl.pack(side="left")

        monto = self._calc_monto(hora_entrada)
        monto_lbl = ctk.CTkLabel(frame, text=f"S/.{monto:.2f}",
                                  font=FONTS["body_bold"],
                                  text_color=COLORS["green"])
        monto_lbl.pack(side="right", padx=10)

        self._rows.append({
            "placa": placa,
            "hora_entrada": hora_entrada,
            "tipo": tipo,
            "frame": frame,
            "time_lbl": time_lbl,
            "monto_lbl": monto_lbl,
        })

    def _elapsed(self, hora_entrada: str) -> str:
        try:
            t0 = datetime.strptime(hora_entrada, "%Y-%m-%d %H:%M:%S")
            delta = datetime.now() - t0
            total = int(delta.total_seconds())
            h = total // 3600
            m = (total % 3600) // 60
            return f"{h:02d}:{m:02d}"
        except Exception:
            return "--:--"

    def _calc_monto(self, hora_entrada: str) -> float:
        try:
            t0 = datetime.strptime(hora_entrada, "%Y-%m-%d %H:%M:%S")
            mins = max(1, int((datetime.now() - t0).total_seconds() / 60))
            return round((mins / 60) * PRECIO_HORA_DEFAULT, 2)
        except Exception:
            return 0.0

    def _schedule_time_refresh(self):
        job = self.after(30_000, self._refresh_times)
        self._after_jobs.append(job)

    def _refresh_times(self):
        for row in self._rows:
            row["time_lbl"].configure(text=self._elapsed(row["hora_entrada"]))
            row["monto_lbl"].configure(text=f"S/.{self._calc_monto(row['hora_entrada']):.2f}")
        self._schedule_time_refresh()
