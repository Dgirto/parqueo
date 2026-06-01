from datetime import datetime
import customtkinter as ctk
from app.core.theme import COLORS, FONTS, RADIUS
from app.core.config import PRECIO_HORA_DEFAULT


class DetectionCard(ctk.CTkFrame):
    def __init__(self, master, on_manual_exit=None, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_card"])
        kwargs.setdefault("corner_radius", RADIUS["card"])
        super().__init__(master, **kwargs)

        self._after_jobs = []
        self._on_manual_exit = on_manual_exit
        self._hora_entrada: datetime | None = None
        self._current_placa: str | None = None
        self._timer_job = None

        self._build()

    def _build(self):
        pad = {"padx": 16}

        # ── Header row ─────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", pady=(14, 0), **pad)
        ctk.CTkLabel(hdr, text="ÚLTIMA DETECCIÓN",
                     font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self._ts_lbl = ctk.CTkLabel(hdr, text="--:--:--",
                                    font=FONTS["mono"],
                                    text_color=COLORS["text_secondary"])
        self._ts_lbl.pack(side="right")

        ctk.CTkFrame(self, height=1, fg_color=COLORS["border"],
                     corner_radius=0).pack(fill="x", pady=(8, 0))

        # ── Plate display ──────────────────────────────────────────
        self._plate_lbl = ctk.CTkLabel(self,
                                       text="- - -  -  - - -",
                                       font=FONTS["display"],
                                       text_color=COLORS["cyan"])
        self._plate_lbl.pack(pady=(14, 6))

        # ── Status badge ───────────────────────────────────────────
        badge_wrap = ctk.CTkFrame(self, fg_color="transparent")
        badge_wrap.pack()
        self._badge = ctk.CTkFrame(badge_wrap,
                                   fg_color=COLORS["border"],
                                   corner_radius=RADIUS["badge"])
        self._badge.pack(ipadx=12, ipady=4)
        self._badge_lbl = ctk.CTkLabel(self._badge, text="SIN DETECCIÓN",
                                       font=FONTS["body_bold"],
                                       text_color=COLORS["text_secondary"])
        self._badge_lbl.pack()

        # ── Timer block ────────────────────────────────────────────
        ctk.CTkLabel(self, text="Tiempo transcurrido",
                     font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack(pady=(16, 0))
        self._timer_lbl = ctk.CTkLabel(self, text="00 : 00 : 00",
                                       font=FONTS["metric"],
                                       text_color=COLORS["text_primary"])
        self._timer_lbl.pack()

        # ── Tarifa / monto ─────────────────────────────────────────
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(pady=(10, 0))
        ctk.CTkLabel(info_frame,
                     text=f"Tarifa: S/. {PRECIO_HORA_DEFAULT:.2f}/hr",
                     font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(anchor="w")
        monto_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        monto_row.pack(anchor="w")
        ctk.CTkLabel(monto_row, text="Monto acumulado: ",
                     font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self._monto_lbl = ctk.CTkLabel(monto_row, text="S/. 0.00",
                                       font=("Segoe UI", 16, "bold"),
                                       text_color=COLORS["green"])
        self._monto_lbl.pack(side="left")

        # ── Manual exit button ─────────────────────────────────────
        self._exit_btn = ctk.CTkButton(
            self,
            text="REGISTRAR SALIDA",
            fg_color=COLORS["border"],
            hover_color=COLORS["red_dim"],
            text_color=COLORS["text_secondary"],
            corner_radius=RADIUS["button"],
            height=40,
            font=FONTS["body_bold"],
            state="disabled",
            command=self._manual_exit,
        )
        self._exit_btn.pack(fill="x", padx=16, pady=(14, 16))

    # ── public API ─────────────────────────────────────────────────

    def update_detection(self, placa: str, hora_entrada: str, accion: str):
        self._current_placa = placa
        try:
            self._hora_entrada = datetime.strptime(hora_entrada, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self._hora_entrada = datetime.now()

        # Display plate with spaced chars
        spaced = "  ".join(placa.replace("-", " - "))
        self._plate_lbl.configure(text=spaced)
        self._ts_lbl.configure(text=self._hora_entrada.strftime("%H:%M:%S"))

        if accion == "ENTRADA":
            self._badge.configure(fg_color="#0D2E1F")
            self._badge_lbl.configure(text=f"● ENTRADA  │  {self._hora_entrada.strftime('%H:%M:%S')}",
                                      text_color=COLORS["green"])
            self._exit_btn.configure(state="normal",
                                     fg_color=COLORS["red"],
                                     text_color=COLORS["text_primary"])
            self._start_timer()
        elif accion == "SALIDA":
            self._badge.configure(fg_color="#2E1010")
            self._badge_lbl.configure(text=f"● SALIDA   │  {datetime.now().strftime('%H:%M:%S')}",
                                      text_color=COLORS["red"])
            job = self.after(3000, self.clear)
            self._after_jobs.append(job)

        self._flash_bg()

    def clear(self):
        self._current_placa = None
        self._hora_entrada = None
        self._plate_lbl.configure(text="- - -  -  - - -")
        self._ts_lbl.configure(text="--:--:--")
        self._badge.configure(fg_color=COLORS["border"])
        self._badge_lbl.configure(text="SIN DETECCIÓN",
                                  text_color=COLORS["text_secondary"])
        self._timer_lbl.configure(text="00 : 00 : 00")
        self._monto_lbl.configure(text="S/. 0.00")
        self._exit_btn.configure(state="disabled",
                                 fg_color=COLORS["border"],
                                 text_color=COLORS["text_secondary"])

    # ── internal ───────────────────────────────────────────────────

    def _start_timer(self):
        if self._timer_job:
            self.after_cancel(self._timer_job)
        self._update_timer()

    def _update_timer(self):
        if self._hora_entrada is None:
            return
        elapsed = datetime.now() - self._hora_entrada
        total_secs = int(elapsed.total_seconds())
        h = total_secs // 3600
        m = (total_secs % 3600) // 60
        s = total_secs % 60
        self._timer_lbl.configure(text=f"{h:02d} : {m:02d} : {s:02d}")

        minutes = max(1, total_secs // 60)
        monto = round((minutes / 60) * PRECIO_HORA_DEFAULT, 2)
        self._monto_lbl.configure(text=f"S/. {monto:.2f}")

        self._timer_job = self.after(1000, self._update_timer)
        self._after_jobs.append(self._timer_job)

    def _flash_bg(self):
        self.configure(fg_color="#0D2A33")
        job1 = self.after(300, lambda: self.configure(fg_color=COLORS["bg_card"]))
        self._after_jobs.append(job1)

    def _manual_exit(self):
        if self._on_manual_exit and self._current_placa:
            self._on_manual_exit(self._current_placa)
