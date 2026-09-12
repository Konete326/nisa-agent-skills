import customtkinter as ctk

class CustomModal(ctk.CTkToplevel):
    def __init__(self, parent, title="Alert", message="", on_confirm=None, on_cancel=None, is_confirm=False, is_password=False):
        super().__init__(parent)
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.is_confirm = is_confirm
        self.is_password = is_password
        self.input_entry = None
        self.title(title)
        self.geometry("380x230" if is_password else "380x200")
        self.resizable(False, False)
        self.configure(fg_color="#0f172a")
        self.transient(parent)
        self.grab_set()
        self._build_interface(title, message)
        self._center_window(parent)

    def _center_window(self, parent):
        self.update_idletasks()
        pos_x = parent.winfo_x() + (parent.winfo_width() - 380) // 2
        pos_y = parent.winfo_y() + (parent.winfo_height() - (230 if self.is_password else 200)) // 2
        self.geometry(f"+{max(0, pos_x)}+{max(0, pos_y)}")

    def _build_interface(self, title_text, message_text):
        container = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=12, border_width=1, border_color="#334155")
        container.pack(fill="both", expand=True, padx=12, pady=12)
        header = ctk.CTkLabel(container, text=title_text, font=("Segoe UI", 14, "bold"), text_color="#f8fafc")
        header.pack(anchor="w", padx=16, pady=(12, 4))
        body = ctk.CTkLabel(container, text=message_text, font=("Segoe UI", 11), text_color="#cbd5e1", wraplength=320, justify="left")
        body.pack(fill="x", padx=16, pady=(0, 8))

        if self.is_password:
            self.input_entry = ctk.CTkEntry(container, placeholder_text="Enter Admin Secret...", show="*", fg_color="#0f172a", text_color="#f8fafc", border_width=1, border_color="#475569", height=32)
            self.input_entry.pack(fill="x", padx=16, pady=(0, 10))
            self.input_entry.bind("<Return>", lambda e: self._handle_confirm())
            self.input_entry.focus_set()

        actions = ctk.CTkFrame(container, fg_color="transparent")
        actions.pack(fill="x", side="bottom", padx=16, pady=10)
        confirm_btn = ctk.CTkButton(actions, text="Confirm" if (self.is_confirm or self.is_password) else "OK", width=80, height=30, corner_radius=6, fg_color="#6366f1", hover_color="#4f46e5", font=("Segoe UI", 11, "bold"), command=self._handle_confirm)
        confirm_btn.pack(side="right", padx=(8, 0))

        if self.is_confirm or self.is_password:
            cancel_btn = ctk.CTkButton(actions, text="Cancel", width=80, height=30, corner_radius=6, fg_color="#334155", hover_color="#475569", font=("Segoe UI", 11), command=self._handle_cancel)
            cancel_btn.pack(side="right")

    def _handle_confirm(self):
        val = self.input_entry.get().strip() if self.input_entry else None
        self.grab_release()
        self.destroy()
        if self.on_confirm:
            if self.is_password:
                self.on_confirm(val)
            else:
                self.on_confirm()

    def _handle_cancel(self):
        self.grab_release()
        self.destroy()
        if self.on_cancel:
            self.on_cancel()
