import customtkinter as ctk
import config

class ChatBar(ctk.CTkFrame):
    def __init__(self, master, on_submit=None, on_admin_toggle=None, on_lang_toggle=None, on_mic_toggle=None, **kwargs):
        super().__init__(master, fg_color="#1e293b", corner_radius=18, border_width=1, border_color="#334155", **kwargs)
        self.on_submit = on_submit
        self.on_admin_toggle = on_admin_toggle
        self.on_lang_toggle = on_lang_toggle
        self.on_mic_toggle = on_mic_toggle
        self.languages = ["UR", "EN", "HI"]
        self.is_mic_active = False
        self._setup_layout()

    def _setup_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.indicator = ctk.CTkLabel(self, text="✦", font=("Segoe UI", 14, "bold"), text_color="#6366f1")
        self.indicator.grid(row=0, column=0, padx=(14, 4), pady=8)

        self.input_field = ctk.CTkEntry(
            self, placeholder_text="Instruct Nisa... (or speak via mic)",
            fg_color="#0f172a", text_color="#f8fafc", placeholder_text_color="#64748b",
            border_width=0, corner_radius=12, font=("Segoe UI", 12), height=42
        )
        self.input_field.grid(row=0, column=1, sticky="ew", padx=4, pady=8)
        self.input_field.bind("<Return>", lambda e: self._trigger_submit())

        self.mic_button = ctk.CTkButton(
            self, text="🎙️", width=38, height=34, corner_radius=10,
            fg_color="#334155", hover_color="#475569", text_color="#38bdf8",
            font=("Segoe UI", 13), command=self._trigger_mic
        )
        self.mic_button.grid(row=0, column=2, padx=3, pady=8)

        def_lang = getattr(config, "DEFAULT_LANG", "UR")
        self.lang_button = ctk.CTkButton(
            self, text=f"🌐 {def_lang}", width=64, height=34, corner_radius=10,
            fg_color="#334155", hover_color="#475569", text_color="#38bdf8",
            font=("Segoe UI", 11, "bold"), command=self._cycle_language
        )
        self.lang_button.grid(row=0, column=3, padx=3, pady=8)

        self.admin_badge = ctk.CTkButton(
            self, text="Admin", width=70, height=34, corner_radius=10,
            fg_color="#334155", hover_color="#475569", text_color="#94a3b8",
            font=("Segoe UI", 11, "bold"), command=self._trigger_admin
        )
        self.admin_badge.grid(row=0, column=4, padx=3, pady=8)

        self.action_button = ctk.CTkButton(
            self, text="➤", width=42, height=42, corner_radius=12,
            fg_color="#6366f1", hover_color="#4f46e5", font=("Segoe UI", 14, "bold"),
            command=self._trigger_submit
        )
        self.action_button.grid(row=0, column=5, padx=(3, 12), pady=8)

    def _trigger_mic(self):
        self.is_mic_active = not self.is_mic_active
        self.set_mic_state(self.is_mic_active)
        if self.on_mic_toggle:
            self.on_mic_toggle(self.is_mic_active)

    def set_mic_state(self, is_active):
        self.is_mic_active = is_active
        if is_active:
            self.mic_button.configure(fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff")
        else:
            self.mic_button.configure(fg_color="#334155", hover_color="#475569", text_color="#38bdf8")

    def set_input_text(self, text):
        self.input_field.delete(0, "end")
        self.input_field.insert(0, str(text))

    def _cycle_language(self):
        from core.voice import voice_engine
        cur = voice_engine.get_language()
        idx = (self.languages.index(cur) + 1) % len(self.languages) if cur in self.languages else 0
        nxt = self.languages[idx]
        voice_engine.set_language(nxt)
        self.lang_button.configure(text=f"🌐 {nxt}")
        if self.on_lang_toggle:
            self.on_lang_toggle(nxt)

    def set_language_display(self, lang):
        self.lang_button.configure(text=f"🌐 {str(lang).upper()}")

    def _trigger_submit(self):
        text_val = self.input_field.get().strip()
        if not text_val:
            return
        self.input_field.delete(0, "end")
        if self.on_submit:
            self.on_submit(text_val)

    def _trigger_admin(self):
        if self.on_admin_toggle:
            self.on_admin_toggle()

    def set_admin_state(self, is_admin):
        if is_admin:
            self.admin_badge.configure(text="Admin Active", fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff")
        else:
            self.admin_badge.configure(text="Admin", fg_color="#334155", hover_color="#475569", text_color="#94a3b8")

    def set_focus(self):
        self.input_field.focus_set()
