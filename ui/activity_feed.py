import time
import customtkinter as ctk

class LogBuffer:
    def __init__(self, feed):
        self.feed = feed

    def get(self, *args, **kwargs):
        return "\n".join(self.feed.log_history)

    def insert(self, index, text):
        for line in text.strip().splitlines():
            if line:
                self.feed.log_history.append(line)

    def delete(self, *args, **kwargs):
        self.feed.log_history.clear()

class ActivityFeed(ctk.CTkFrame):
    EVENT_COLORS = {
        "TASK": "#38bdf8",
        "EXEC": "#818cf8",
        "AI": "#c084fc",
        "DONE": "#34d399",
        "WARN": "#fbbf24",
        "ERROR": "#f87171"
    }

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="#1e293b", corner_radius=18, border_width=1, border_color="#334155", **kwargs)
        self.log_history = []
        self.textbox = LogBuffer(self)
        self._init_layout()

    def _init_layout(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header_bar = ctk.CTkFrame(self, fg_color="transparent", height=30)
        header_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        header_bar.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(header_bar, text="Task Stream & Telemetry", font=("Segoe UI", 11, "bold"), text_color="#94a3b8")
        title.grid(row=0, column=0, sticky="w")

        self.copy_button = ctk.CTkButton(
            header_bar, text="Copy", width=54, height=24, corner_radius=6,
            fg_color="#334155", hover_color="#475569", font=("Segoe UI", 10), text_color="#e2e8f0", command=self.copy_logs
        )
        self.copy_button.grid(row=0, column=1, padx=(0, 6), sticky="e")

        self.clear_button = ctk.CTkButton(
            header_bar, text="Clear", width=54, height=24, corner_radius=6,
            fg_color="#334155", hover_color="#475569", font=("Segoe UI", 10), text_color="#e2e8f0", command=self.clear_stream
        )
        self.clear_button.grid(row=0, column=2, sticky="e")

        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=10)
        self.scroll_container.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 12))
        self.scroll_container.grid_columnconfigure(0, weight=1)

    def append_event(self, category, message=""):
        timestamp = time.strftime("%H:%M:%S")
        cat_clean = category.strip("[]").upper()
        badge_color = self.EVENT_COLORS.get(cat_clean, "#38bdf8")
        entry = f"[{timestamp}] [{cat_clean}] {message}".strip() if message else category
        self.log_history.append(entry)

        item_card = ctk.CTkFrame(self.scroll_container, fg_color="#0f172a", corner_radius=8)
        item_card.pack(fill="x", pady=2, padx=4)
        item_card.grid_columnconfigure(1, weight=1)

        badge = ctk.CTkLabel(
            item_card, text=f" {cat_clean[:8]} ", font=("Segoe UI", 9, "bold"),
            text_color="#ffffff", fg_color=badge_color, corner_radius=4
        )
        badge.grid(row=0, column=0, padx=6, pady=6, sticky="nw")

        formatted_text = f"[{timestamp}] {message}" if message else category
        text_label = ctk.CTkLabel(
            item_card, text=formatted_text, font=("Consolas", 10),
            text_color="#f8fafc", wraplength=480, justify="left"
        )
        text_label.grid(row=0, column=1, padx=(4, 8), pady=6, sticky="w")

    def copy_logs(self):
        text = self.textbox.get("1.0", "end-1c").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
            self.copy_button.configure(text="Copied!", fg_color="#10b981", hover_color="#059669")
            self.after(1500, self._reset_copy_button)

    def _reset_copy_button(self):
        self.copy_button.configure(text="Copy", fg_color="#334155", hover_color="#475569")

    def clear_stream(self):
        self.log_history.clear()
        for widget in self.scroll_container.winfo_children():
            widget.destroy()
