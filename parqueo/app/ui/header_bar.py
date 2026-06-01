from datetime import datetime
import customtkinter as ctk
from app.core.theme import COLORS, FONTS


class HeaderBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_header"])
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("height", 56)
        super().__init__(master, **kwargs)
        self.pack_propagate(False)

        self._after_jobs = []
        self._blink_state = True

        # ── bottom border ──────────────────────────────────────────
        border = ctk.CTkFrame(self, height=1, corner_radius=0,
                              fg_color=COLORS["border_bright"])
        border.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")

        # ── LEFT: brand ────────────────────────────────────────────
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=(16, 0))

        ctk.CTkLabel(left, text="🅿  SmartPark",
                     font=FONTS["title"],
                     text_color=COLORS["cyan"]).pack(side="left")
        ctk.CTkLabel(left, text="  ·  Control Center",
                     font=FONTS["subtitle"],
                     text_color=COLORS["text_secondary"]).pack(side="left")

        # ── CENTER: metrics ────────────────────────────────────────
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        self._dentro_val  = self._metric_block(center, "DENTRO",      "0",  COLORS["cyan"],  "vehículos")
        self._sep1        = self._vsep(center)
        self._disp_val    = self._metric_block(center, "DISPONIBLES", "20/20", COLORS["green"], "espacios")
        self._sep2        = self._vsep(center)
        self._cobros_val  = self._metric_block(center, "HOY",         "0",  COLORS["amber"], "cobros")
        self._total_label = None   # set inside _metric_block for HOY

        # ── RIGHT: live indicator + clock ──────────────────────────
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=(0, 20))

        self._live_dot = ctk.CTkLabel(right, text="●",
                                      font=FONTS["subtitle"],
                                      text_color=COLORS["green"])
        self._live_dot.pack(side="left")
        ctk.CTkLabel(right, text=" EN VIVO  ",
                     font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack(side="left")

        clock_col = ctk.CTkFrame(right, fg_color="transparent")
        clock_col.pack(side="left")
        self._clock_lbl = ctk.CTkLabel(clock_col, text="00:00:00",
                                       font=FONTS["mono"],
                                       text_color=COLORS["text_primary"])
        self._clock_lbl.pack()
        self._date_lbl = ctk.CTkLabel(clock_col, text="",
                                      font=FONTS["small"],
                                      text_color=COLORS["text_secondary"])
        self._date_lbl.pack()

        self._start_blink()
        self._update_clock()

    # ── helpers ────────────────────────────────────────────────────

    def _metric_block(self, parent, label: str, value: str,
                      val_color: str, sublabel: str) -> ctk.CTkLabel:
        frame = ctk.CTkFrame(parent, fg_color="transparent", width=110)
        frame.pack(side="left", padx=14)
        frame.pack_propagate(False)

        ctk.CTkLabel(frame, text=label,
                     font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack()
        val_lbl = ctk.CTkLabel(frame, text=value,
                               font=FONTS["metric"],
                               text_color=val_color)
        val_lbl.pack()
        ctk.CTkLabel(frame, text=sublabel,
                     font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack()
        return val_lbl

    @staticmethod
    def _vsep(parent) -> ctk.CTkFrame:
        sep = ctk.CTkFrame(parent, width=1, height=36, corner_radius=0,
                           fg_color=COLORS["border_bright"])
        sep.pack(side="left", padx=4)
        sep.pack_propagate(False)
        return sep

    # ── public API ─────────────────────────────────────────────────

    def update_metrics(self, dentro: int, disponibles: int,
                       cobros_hoy: int, total_hoy: float):
        total_espacios = dentro + disponibles
        self._dentro_val.configure(text=str(dentro))
        self._disp_val.configure(text=f"{disponibles}/{total_espacios}")
        self._cobros_val.configure(text=str(cobros_hoy))

    # ── internal timers ────────────────────────────────────────────

    def _start_blink(self):
        job = self.after(800, self._blink)
        self._after_jobs.append(job)

    def _blink(self):
        current = self._live_dot.cget("text_color")
        next_color = (COLORS["green"]
                      if current != COLORS["green"]
                      else COLORS["bg_card"])
        self._live_dot.configure(text_color=next_color)
        job = self.after(800, self._blink)
        self._after_jobs.append(job)

    def _update_clock(self):
        now = datetime.now()
        self._clock_lbl.configure(text=now.strftime("%H:%M:%S"))
        self._date_lbl.configure(text=now.strftime("%d/%m/%Y"))
        job = self.after(1000, self._update_clock)
        self._after_jobs.append(job)
