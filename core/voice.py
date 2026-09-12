import os
import time
import queue
import asyncio
import tempfile
import threading
import pygame
import edge_tts
import config

LOCALIZED_STATUS = {
    "UR": {"start": "Kaam shuru ho gaya hai", "running": "Kaam jaari hai", "complete": "Task mukammal ho gaya"},
    "EN": {"start": "Task initiated", "running": "Executing task", "complete": "Task completed"},
    "HI": {"start": "Kaarya prarambh ho gaya hai", "running": "Kaarya chal raha hai", "complete": "Kaarya poora hua"}
}

class VoiceEngine:
    def __init__(self):
        self.message_queue = queue.Queue()
        self.current_lang = getattr(config, "DEFAULT_LANG", "UR")
        self.worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.worker_thread.start()

    def set_language(self, lang_code):
        clean = str(lang_code).upper().strip()
        if clean in getattr(config, "VOICE_MAP", {}):
            self.current_lang = clean
            return True
        return False

    def get_language(self):
        return self.current_lang

    def speak(self, text, lang=None):
        if text and str(text).strip():
            target_lang = (lang or self.current_lang).upper().strip()
            self.message_queue.put((str(text).strip(), target_lang))

    def _speech_worker(self):
        try: pygame.mixer.init()
        except Exception: pass
        while True:
            item = self.message_queue.get()
            if item is None: break
            text, lang = item
            voice_map = getattr(config, "VOICE_MAP", {})
            voice = voice_map.get(lang, voice_map.get("UR", "ur-PK-UzmaNeural"))
            temp_path = None
            try:
                fd, temp_path = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)
                asyncio.run(edge_tts.Communicate(text, voice).save(temp_path))
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy(): time.sleep(0.04)
                    pygame.mixer.music.unload()
            except Exception: pass
            finally:
                if temp_path and os.path.exists(temp_path):
                    try: os.remove(temp_path)
                    except Exception: pass
                self.message_queue.task_done()

    def notify_task_start(self):
        phrases = LOCALIZED_STATUS.get(self.current_lang, LOCALIZED_STATUS["UR"])
        self.speak(phrases["start"])

    def notify_task_running(self, detail=""):
        phrases = LOCALIZED_STATUS.get(self.current_lang, LOCALIZED_STATUS["UR"])
        msg = f"{phrases['running']} {detail}".strip() if detail else phrases["running"]
        self.speak(msg)

    def notify_task_complete(self):
        phrases = LOCALIZED_STATUS.get(self.current_lang, LOCALIZED_STATUS["UR"])
        self.speak(phrases["complete"])

    def notify_task_acknowledged(self, instruction=""): self.notify_task_start()
    def notify_action_executing(self, action=""): self.notify_task_running(action)
    def notify_task_completed(self, summary=""): self.notify_task_complete()

voice_engine = VoiceEngine()
