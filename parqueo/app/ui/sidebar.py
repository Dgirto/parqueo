import customtkinter as ctk
from app.core.theme import COLORS, FONTS, RADIUS


_NAV_ITEMS = [
    ("📹", "En Vivo",    "live"),
    ("📋", "Registros",  "records"),
    ("💲", "Tarifas",    "rates"),
    ("⚙️",  "Config",    "config"),
]


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navigate=None, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_sidebar"])
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("width", 200)
        super().__init__(master, **kwargs)
        self.pack_propagate(False)
        self.grid_propagate(False)

        self._after_jobs = []
        self._on_navigate = on_navigate
        self._active_key = "live"
        self._buttons: dict[str, tuple] = {}   # key → (wrapper, btn, indicator)

        # ── Logo zone ──────────────────────────────────────────────
        logo_zone = ctk.CTkFrame(self, fg_color="transparent", height=56)
        logo_zone.pack(fill="x")
        logo_zone.pack_propagate(False)
        ctk.CTkLabel(logo_zone, text="🅿",
                     font=("Segoe UI", 28, "bold"),
                     text_color=COLORS["cyan"]).pack(expand=True)

        ctk.CTkFrame(self, height=1, corner_radius=0,
                     fg_color=COLORS["border"]).pack(fill="x")

        # ── Nav buttons ────────────────────────────────────────────
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", pady=(8, 0))

        for icon, label, key in _NAV_ITEMS:
            self._make_nav_button(nav_frame, icon, label, key)

        # ── Spacer ─────────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)

        # ── Status zone ────────────────────────────────────────────
        status_card = ctk.CTkFrame(self, fg_color=COLORS["bg_card"],
                                   corner_radius=RADIUS["card"])
        status_card.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(status_card, text="SISTEMA",
                     font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack(anchor="w", padx=10, pady=(8, 0))
        ctk.CTkLabel(status_card, text="● Operativo",
                     font=FONTS["small"],
                     text_color=COLORS["green"]).pack(anchor="w", padx=10)
        ctk.CTkLabel(status_card, text="Cám. 01: OK",
                     font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack(anchor="w", padx=10, pady=(0, 8))

        # ── Exit button ────────────────────────────────────────────
        exit_btn = ctk.CTkButton(
            self, text="  🚪  Salir",
            fg_color="transparent",
            hover_color=COLORS["red_dim"],
            text_color=COLORS["text_secondary"],
            anchor="w",
            corner_radius=RADIUS["button"],
            height=44,
            font=FONTS["sidebar"],
            command=master.winfo_toplevel().destroy,
        )
        exit_btn.pack(fill="x", padx=8, pady=(0, 12))

        # Highlight initial active button
        self.set_active("live")

    # ── helpers ────────────────────────────────────────────────────

    def _make_nav_button(self, parent, icon: str, label: str, key: str):
        wrapper = ctk.CTkFrame(parent, fg_color="transparent", height=44)
        wrapper.pack(fill="x", pady=2, padx=8)
        wrapper.pack_propagate(False)

        # Left accent indicator (3 px wide, hidden by default)
        indicator = ctk.CTkFrame(wrapper, width=3, height=44,
                                 fg_color="transparent", corner_radius=2)
        indicator.pack(side="left")
        indicator.pack_propagate(False)

        btn = ctk.CTkButton(
            wrapper,
            text=f"  {icon}  {label}",
            fg_color="transparent",
            hover_color=COLORS["bg_card"],
            text_color=COLORS["text_secondary"],
            anchor="w",
            corner_radius=RADIUS["button"],
            height=44,
            font=FONTS["sidebar"],
            command=lambda k=key: self._navigate(k),
        )
        btn.pack(side="left", fill="both", expand=True)
        self._buttons[key] = (wrapper, btn, indicator)

    def _navigate(self, key: str):
        self.set_active(key)
        if self._on_navigate:
            self._on_navigate(key)

    # ── public API ─────────────────────────────────────────────────

    def set_active(self, section_key: str):
        # Deactivate previous
        if self._active_key in self._buttons:
            _, btn, indicator = self._buttons[self._active_key]
            btn.configure(fg_color="transparent",
                          text_color=COLORS["text_secondary"])
            indicator.configure(fg_color="transparent")

        # Activate new
        self._active_key = section_key
        if section_key in self._buttons:
            _, btn, indicator = self._buttons[section_key]
            btn.configure(fg_color=COLORS["bg_card"],
                          text_color=COLORS["cyan"])
            indicator.configure(fg_color=COLORS["cyan"])
