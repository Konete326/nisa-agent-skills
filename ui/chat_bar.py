import customtkinter as ctk

class ChatBar(ctk.CTkFrame):
    def __init__(self, master, on_submit=None, on_admin_toggle=None, **kwargs):
        super().__init__(
            master,
            fg_color="#1e293b",
            corner_radius=18,
            border_width=1,
            border_color="#334155",
            **kwargs
        )
        self.on_submit = on_submit
        self.on_admin_toggle = on_admin_toggle
        self._setup_layout()

    def _setup_layout(self):
        self.grid_columnconfigure(1, weight=1)

        self.indicator = ctk.CTkLabel(
            self,
            text="✦",
            font=("Segoe UI", 14, "bold"),
            text_color="#6366f1"
        )
        self.indicator.grid(row=0, column=0, padx=(16, 6), pady=8)

        self.input_field = ctk.CTkEntry(
            self,
            placeholder_text="Instruct Nisa... (e.g., 'launch notepad', 'inspect system')",
            fg_color="#0f172a",
            text_color="#f8fafc",
            placeholder_text_color="#64748b",
            border_width=0,
            corner_radius=12,
            font=("Segoe UI", 12),
            height=42
        )
        self.input_field.grid(row=0, column=1, sticky="ew", padx=6, pady=8)
        self.input_field.bind("<Return>", lambda event: self._trigger_submit())

        self.admin_badge = ctk.CTkButton(
            self,
            text="Admin",
            width=70,
            height=32,
            corner_radius=10,
            fg_color="#334155",
            hover_color="#475569",
            text_color="#94a3b8",
            font=("Segoe UI", 11, "bold"),
            command=self._trigger_admin
        )
        self.admin_badge.grid(row=0, column=2, padx=(4, 6), pady=8)

        self.action_button = ctk.CTkButton(
            self,
            text="➤",
            width=42,
            height=42,
            corner_radius=12,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            font=("Segoe UI", 14, "bold"),
            command=self._trigger_submit
        )
        self.action_button.grid(row=0, column=3, padx=(2, 12), pady=8)

    def _trigger_submit(self):
        text_value = self.input_field.get().strip()
        if not text_value:
            return
        self.input_field.delete(0, "end")
        if self.on_submit:
            self.on_submit(text_value)

    def _trigger_admin(self):
        if self.on_admin_toggle:
            self.on_admin_toggle()

    def set_admin_state(self, is_admin):
        if is_admin:
            self.admin_badge.configure(
                text="Admin Active",
                fg_color="#ef4444",
                hover_color="#dc2626",
                text_color="#ffffff"
            )
        else:
            self.admin_badge.configure(
                text="Admin",
                fg_color="#334155",
                hover_color="#475569",
                text_color="#94a3b8"
            )

    def set_focus(self):
        self.input_field.focus_set()
