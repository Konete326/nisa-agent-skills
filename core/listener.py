import threading
import speech_recognition as sr
import config
from core.voice import voice_engine

LANG_MAP = {
    "UR": "ur-PK",
    "EN": "en-US",
    "HI": "hi-IN"
}

class VoiceListener:
    def __init__(self, on_transcribed=None):
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.on_transcribed = on_transcribed
        self.is_listening = False
        self.stop_fn = None
        self.lock = threading.Lock()

    def set_callback(self, callback):
        self.on_transcribed = callback

    def start_listening(self):
        with self.lock:
            if self.is_listening:
                return True
            try:
                mic = sr.Microphone()
                with mic as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
                self.is_listening = True
                self.stop_fn = self.recognizer.listen_in_background(mic, self._audio_callback, phrase_time_limit=8)
                return True
            except Exception:
                self.is_listening = False
                return False

    def stop_listening(self):
        with self.lock:
            if not self.is_listening:
                return False
            self.is_listening = False
            if self.stop_fn:
                try:
                    self.stop_fn(wait_for_stop=False)
                except Exception:
                    pass
                self.stop_fn = None
            return True

    def toggle_listening(self):
        return self.stop_listening() if self.is_listening else self.start_listening()

    def _audio_callback(self, recognizer, audio):
        if not self.is_listening:
            return
        lang_key = getattr(voice_engine, "current_lang", getattr(config, "DEFAULT_LANG", "UR")).upper()
        target_lang = LANG_MAP.get(lang_key, "ur-PK")
        try:
            transcribed = recognizer.recognize_google(audio, language=target_lang)
            clean_text = str(transcribed).strip()
            if clean_text and self.on_transcribed:
                self.on_transcribed(clean_text)
        except (sr.UnknownValueError, sr.RequestError, Exception):
            pass

voice_listener = VoiceListener()
