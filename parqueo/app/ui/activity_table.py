import customtkinter as ctk
from app.core.theme import COLORS, FONTS, RADIUS
from app.database.models import Ticket

_COLS = [
    ("PLACA",    120),
    ("TIPO",      70),
    ("ENTRADA",  100),
    ("SALIDA",   100),
    ("TIEMPO",    80),
    ("MONTO",     90),
    ("ESTADO",    90),
]
_MAX_ROWS = 50


class ActivityTable(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_card"])
        kwargs.setdefault("corner_radius", RADIUS["card"])
        super().__init__(master, **kwargs)

        self._after_jobs = []
        self._row_frames: list[ctk.CTkFrame] = []

        # ── Column headers ─────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="#14161E", corner_radius=0, height=32)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        for i, (col, width) in enumerate(_COLS):
            ctk.CTkLabel(hdr, text=col, width=width,
                         font=("Segoe UI", 10, "bold"),
                         text_color=COLORS["text_secondary"],
                         anchor="w").pack(side="left", padx=(10 if i == 0 else 2, 0))
            if i < len(_COLS) - 1:
                ctk.CTkFrame(hdr, width=1, height=20, corner_radius=0,
                             fg_color=COLORS["border"]).pack(side="left", padx=2)

        # ── Scroll body ────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                              label_text="")
        self._scroll.pack(fill="both", expand=True, padx=0, pady=(0, 0))

    # ── public API ─────────────────────────────────────────────────

    def prepend_row(self, ticket: Ticket):
        self._insert_row(ticket, index=0, highlight=True)
        # Enforce max rows
        while len(self._row_frames) > _MAX_ROWS:
            oldest = self._row_frames.pop()
            oldest.destroy()

    def refresh(self, tickets: list):
        for w in self._scroll.winfo_children():
            w.destroy()
        self._row_frames.clear()
        for i, ticket in enumerate(tickets):
            self._insert_row(ticket, index=i, highlight=False)

    def highlight_row(self, placa: str):
        for frame in self._row_frames:
            if getattr(frame, "_placa", None) == placa:
                frame.configure(fg_color="#0D2A33")
                job = self.after(2000, lambda f=frame, bg=frame._orig_bg:
                                 f.configure(fg_color=bg))
                self._after_jobs.append(job)

    # ── internal ───────────────────────────────────────────────────

    def _insert_row(self, ticket: Ticket, index: int, highlight: bool):
        bg = COLORS["bg_row_even"] if index % 2 == 0 else COLORS["bg_row_odd"]
        row = ctk.CTkFrame(self._scroll, fg_color=bg,
                           corner_radius=4, height=34)
        row._placa = ticket.placa
        row._orig_bg = bg
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)

        # Hover
        row.bind("<Enter>", lambda e, r=row: r.configure(fg_color=COLORS["bg_row_hover"]))
        row.bind("<Leave>", lambda e, r=row, b=bg: r.configure(fg_color=b))

        # ── Cells ──────────────────────────────────────────────────
        # PLACA
        ctk.CTkLabel(row, text=ticket.placa, width=120,
                     font=FONTS["body_bold"],
                     text_color=COLORS["text_primary"],
                     anchor="w").pack(side="left", padx=(10, 2))

        # TIPO
        ctk.CTkLabel(row, text="AUTO", width=70,
                     font=FONTS["small"],
                     text_color=COLORS["text_secondary"],
                     anchor="w").pack(side="left", padx=2)

        # ENTRADA
        entrada = ticket.hora_entrada[-8:] if ticket.hora_entrada else "--"
        ctk.CTkLabel(row, text=entrada, width=100,
                     font=FONTS["mono"],
                     text_color=COLORS["text_secondary"],
                     anchor="w").pack(side="left", padx=2)

        # SALIDA
        salida = ticket.hora_salida[-8:] if ticket.hora_salida else "--"
        ctk.CTkLabel(row, text=salida, width=100,
                     font=FONTS["mono"],
                     text_color=COLORS["text_secondary"],
                     anchor="w").pack(side="left", padx=2)

        # TIEMPO
        mins = ticket.minutos or 0
        tiempo = f"{mins // 60}h {mins % 60:02d}m" if mins else "--"
        ctk.CTkLabel(row, text=tiempo, width=80,
                     font=FONTS["small"],
                     text_color=COLORS["text_secondary"],
                     anchor="w").pack(side="left", padx=2)

        # MONTO
        is_closed = ticket.estado == "CERRADO"
        monto_txt = f"S/.{ticket.monto:.2f}" if ticket.monto is not None else "--"
        monto_color = COLORS["green"] if is_closed else COLORS["amber"]
        ctk.CTkLabel(row, text=monto_txt, width=90,
                     font=FONTS["small"],
                     text_color=monto_color,
                     anchor="w").pack(side="left", padx=2)

        # ESTADO badge
        badge_bg  = "#0D2E1F" if is_closed else "#1A1A0A"
        badge_txt = COLORS["green"] if is_closed else COLORS["amber"]
        badge = ctk.CTkFrame(row, fg_color=badge_bg, corner_radius=6)
        badge.pack(side="left", padx=6)
        ctk.CTkLabel(badge, text=ticket.estado,
                     font=("Segoe UI", 9, "bold"),
                     text_color=badge_txt).pack(padx=6, pady=2)

        # New-row flash
        if highlight:
            row.configure(fg_color="#0D2A33")
            job = self.after(2000, lambda r=row, b=bg: r.configure(fg_color=b))
            self._after_jobs.append(job)

        # Insert at top using pack re-ordering trick
        if index == 0 and self._row_frames:
            row.pack_forget()
            row.pack(fill="x", pady=1, before=self._row_frames[0])

        self._row_frames.insert(0 if index == 0 else len(self._row_frames), row)
