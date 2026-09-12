import customtkinter as ctk
import config
from core.engine import orchestration_engine
from ui.chat_bar import ChatBar
from ui.activity_feed import ActivityFeed
from ui.modal import CustomModal
from core.voice import voice_engine

class NisaDesktopApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{config.AGENT_NAME} AI Operator")
        self.geometry("740x520")
        self.minsize(620, 400)
        self.configure(fg_color="#090d16")
        ctk.set_appearance_mode("Dark")

        self.engine = orchestration_engine
        self._setup_view()
        self._bind_engine_telemetry()
        self._initialize_system()

    def _setup_view(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top_header = ctk.CTkFrame(self, fg_color="transparent", height=38)
        top_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 2))
        top_header.grid_columnconfigure(1, weight=1)

        brand_badge = ctk.CTkLabel(
            top_header,
            text=f"● {config.AGENT_NAME} OS",
            font=("Segoe UI", 13, "bold"),
            text_color="#6366f1"
        )
        brand_badge.grid(row=0, column=0, sticky="w")

        self.status_display = ctk.CTkLabel(
            top_header,
            text="Nisa is ready",
            font=("Segoe UI", 11, "bold"),
            text_color="#10b981"
        )
        self.status_display.grid(row=0, column=1, sticky="e")

        self.chat_bar = ChatBar(self, on_submit=self._dispatch_user_input)
        self.chat_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(6, 10))

        self.activity_stream = ActivityFeed(self)
        self.activity_stream.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 14))

    def _bind_engine_telemetry(self):
        self.engine.register_log_listener(
            lambda category, text: self.after(0, self.activity_stream.append_event, category, text)
        )
        self.engine.register_status_listener(
            lambda status_text: self.after(0, self._update_status_ui, status_text)
        )

    def _update_status_ui(self, status_text):
        is_busy = "executing" in status_text.lower()
        badge_color = "#f59e0b" if is_busy else "#10b981"
        self.status_display.configure(text=status_text, text_color=badge_color)

    def _initialize_system(self):
        loaded_count = len(self.engine.loader.registry)
        self.activity_stream.append_event("SYSTEM", f"Agent initialized with {loaded_count} native skills.")
        if config.GEMINI_API_KEY:
            self.activity_stream.append_event("AI", "Gemini 3.6 Flash operational.")
        else:
            self.activity_stream.append_event("WARN", "GEMINI_API_KEY not found in environment.")
        voice_engine.speak(f"{config.AGENT_NAME} OS is ready")
        self.chat_bar.set_focus()

    def _dispatch_user_input(self, user_command):
        if user_command.lower().startswith("security "):
            CustomModal(self, title="Security Status", message="Zero-trust security module is active.", is_confirm=False)
            return

        self.engine.submit_task_async(user_command)

def main():
    app = NisaDesktopApp()
    app.mainloop()

if __name__ == "__main__":
    main()
