import queue
import threading
import pythoncom
import win32com.client
import config

class VoiceEngine:
    def __init__(self):
        self.message_queue = queue.Queue()
        self.volume = getattr(config, "VOICE_VOLUME", 90)
        self.rate = getattr(config, "VOICE_RATE", 1)
        self.worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.worker_thread.start()

    def _speech_worker(self):
        pythoncom.CoInitialize()
        speaker = None
        try:
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Volume = self.volume
            speaker.Rate = self.rate
        except Exception:
            speaker = None

        while True:
            text = self.message_queue.get()
            if text is None:
                break
            if speaker and text:
                try:
                    speaker.Speak(str(text))
                except Exception:
                    pass
            self.message_queue.task_done()
        pythoncom.CoUninitialize()

    def speak(self, text):
        if text and str(text).strip():
            self.message_queue.put(str(text).strip())

    def notify_task_acknowledged(self, instruction):
        clean_text = str(instruction)[:50]
        self.speak(f"Task acknowledged: {clean_text}")

    def notify_action_executing(self, action):
        clean_act = str(action)[:40]
        self.speak(f"Executing {clean_act}")

    def notify_task_completed(self, summary):
        clean_sum = str(summary)[:50]
        self.speak(f"Task completed: {clean_sum}")

voice_engine = VoiceEngine()
