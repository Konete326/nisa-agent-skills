import customtkinter as ctk
import config
from core.engine import orchestration_engine
from core.listener import voice_listener
from core.voice import voice_engine
from ui.chat_bar import ChatBar
from ui.activity_feed import ActivityFeed
from ui.modal import CustomModal

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
        top = ctk.CTkFrame(self, fg_color="transparent", height=38)
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 2))
        top.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(top, text=f"● {config.AGENT_NAME} OS", font=("Segoe UI", 13, "bold"), text_color="#6366f1").grid(row=0, column=0, sticky="w")
        self.status_display = ctk.CTkLabel(top, text="Nisa is ready", font=("Segoe UI", 11, "bold"), text_color="#10b981")
        self.status_display.grid(row=0, column=1, sticky="e")
        self.chat_bar = ChatBar(self, on_submit=self._dispatch_user_input, on_admin_toggle=self._handle_admin_click, on_lang_toggle=self._handle_lang_change, on_mic_toggle=self._handle_mic_toggle)
        self.chat_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(6, 10))
        self.activity_stream = ActivityFeed(self)
        self.activity_stream.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 14))

    def _bind_engine_telemetry(self):
        self.engine.register_log_listener(lambda cat, text: self.after(0, self.activity_stream.append_event, cat, text))
        self.engine.register_status_listener(lambda text: self.after(0, self._update_status_ui, text))
        voice_listener.set_callback(lambda text: self.after(0, self._handle_voice_input, text))

    def _update_status_ui(self, status_text):
        if self.chat_bar.is_mic_active and "listening" in status_text.lower():
            self.status_display.configure(text=status_text, text_color="#ef4444")
            return
        if self.engine.admin_mode and "ready" in status_text.lower():
            status_text = "Nisa (Admin Mode Active)"
        is_busy = "executing" in status_text.lower()
        badge_color = "#f59e0b" if is_busy else ("#ef4444" if self.engine.admin_mode else "#10b981")
        self.status_display.configure(text=status_text, text_color=badge_color)

    def _initialize_system(self):
        loaded_count = len(self.engine.loader.registry)
        self.activity_stream.append_event("SYSTEM", f"Agent initialized with {loaded_count} native skills.")
        ai_msg = "Gemini intelligence engine operational." if config.GEMINI_API_KEY else "GEMINI_API_KEY not found."
        self.activity_stream.append_event("AI" if config.GEMINI_API_KEY else "WARN", ai_msg)
        voice_engine.speak(f"{config.AGENT_NAME} OS is ready")
        self.chat_bar.set_focus()

    def _handle_lang_change(self, lang):
        self.activity_stream.append_event("VOICE", f"Language switched to {lang}.")

    def _handle_mic_toggle(self, is_active):
        if is_active:
            if voice_listener.start_listening():
                self._update_status_ui("Nisa is listening...")
                self.activity_stream.append_event("VOICE", "Continuous speech recognition active.")
            else:
                self.chat_bar.set_mic_state(False)
                self.activity_stream.append_event("ERROR", "Microphone access error.")
        else:
            voice_listener.stop_listening()
            self._update_status_ui("Nisa is ready")
            self.activity_stream.append_event("VOICE", "Microphone paused.")

    def _handle_voice_input(self, text):
        self.chat_bar.set_input_text(text)
        self.activity_stream.append_event("VOICE", f"Heard: '{text}'")
        self._dispatch_user_input(text)

    def _handle_admin_click(self):
        if self.engine.admin_mode:
            self.engine.admin_mode = False
            self.chat_bar.set_admin_state(False)
            self._update_status_ui("Nisa is ready")
            self.activity_stream.append_event("SYSTEM", "Normal Mode active.")
            voice_engine.speak("Admin mode deactivated.")
        else:
            CustomModal(self, title="Admin Authentication", message="Enter Admin Secret:", on_confirm=self._verify_admin_password, is_password=True)

    def _verify_admin_password(self, secret_input):
        if secret_input and secret_input == config.ADMIN_SECRET:
            self.engine.admin_mode = True
            self.chat_bar.set_admin_state(True)
            self._update_status_ui("Nisa (Admin Mode Active)")
            self.activity_stream.append_event("SECURITY", "Admin Mode enabled.")
            voice_engine.speak("Admin mode activated.")
        else:
            CustomModal(self, title="Access Denied", message="Invalid admin credentials.")
            self.activity_stream.append_event("ERROR", "Invalid admin authentication.")
            voice_engine.speak("Access denied.")

    def _dispatch_user_input(self, user_command):
        if user_command.lower().startswith("security "):
            CustomModal(self, title="Security Status", message="Zero-trust security module is active.")
            return
        self.engine.submit_task_async(user_command)

if __name__ == "__main__":
    NisaDesktopApp().mainloop()
