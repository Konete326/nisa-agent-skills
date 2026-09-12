import threading
import shutil
from datetime import datetime
from bson import ObjectId
from core.security import security_service
from core.executor import native_executor
from core.advisor import gemini_advisor
from core.dynamic_loader import skill_loader
from core.voice import voice_engine
import config

STAGE_MSGS = {
    "start": {"UR": "{} khol kar kaam shuru kar rahi hoon", "EN": "Working on {} execution", "HI": "{} par karya prarambh kar rahi hoon"},
    "running": {"UR": "{} par kaam jaari hai", "EN": "Executing operations on {}", "HI": "{} par karya chal raha hai"},
    "done": {"UR": "{} kamyabi se mukammal ho gaya", "EN": "{} completed successfully", "HI": "{} safaltapoorvak poora hua"},
    "fail": {"UR": "{} mukammal nahi ho saka", "EN": "{} execution failed", "HI": "{} vifal raha"}
}

class TaskEngine:
    def __init__(self):
        self.security, self.executor = security_service, native_executor
        self.advisor, self.loader = gemini_advisor, skill_loader
        self.listeners, self.status_listeners = [], []
        self.active_tasks_count, self.admin_mode = 0, False

    def register_log_listener(self, cb): self.listeners.append(cb)
    def register_status_listener(self, cb): self.status_listeners.append(cb)

    def notify_status(self, text):
        for l in self.status_listeners:
            try: l(text)
            except Exception: pass

    def log(self, event_type, message):
        for l in self.listeners:
            try: l(event_type.upper(), message)
            except Exception: pass

    def submit_task_async(self, instruction, completion_callback=None):
        threading.Thread(target=self._process_task_pipeline, args=(instruction, completion_callback), daemon=True).start()

    def _identify_target(self, query):
        return next((a for a in ("notepad", "excel", "chrome", "calc", "word", "powerpoint", "cmd", "terminal") if a in query.lower()), None)

    def _narrate(self, stage, app, ok=True):
        st = stage if stage != "finish" else ("done" if ok else "fail")
        lang = getattr(voice_engine, "get_language", lambda: "UR")()
        tmpl = STAGE_MSGS.get(st, {}).get(lang, STAGE_MSGS[st]["UR"])
        voice_engine.speak(tmpl.format(app.capitalize() if app else "Task"))

    def _process_task_pipeline(self, raw_instruction, on_finish=None):
        self.active_tasks_count += 1
        self.notify_status("Nisa is executing")
        sanitized = self.security.sanitize(raw_instruction)
        target_app = self._identify_target(sanitized or "")
        if not sanitized:
            self.log("ERROR", "Received empty task payload")
            self._finalize_task(on_finish, {"success": False, "status": "rejected"}, target_app)
            return
        self._narrate("start", target_app)
        self.log("TASK", f"Processing: {sanitized}")
        rid = self._save_task_record(sanitized, "running")
        result = self._route_instruction(sanitized, target_app)
        flag = "completed" if result.get("success", False) else "failed"
        self._update_task_record(rid, flag, result)
        self.log("DONE" if result.get("success") else "WARN", str(result))
        self._finalize_task(on_finish, result, target_app)

    def _route_instruction(self, query, app):
        clean, lowered = query.strip(), query.strip().lower()
        if lowered.startswith("train ") or lowered.startswith("learn "):
            from evolution.trainer import software_trainer
            return software_trainer.train_skill(clean)
        candidate = app or lowered.replace("launch ", "").replace("open ", "").strip()
        if self.admin_mode and (candidate in ("notepad", "excel") or shutil.which(candidate)):
            sk = self.loader.registry.get(candidate)
            ver = sk.get("metadata", {}).get("version", "1.0.0") if sk else "0.0.0"
            if not sk or ver < "2.0.0":
                voice_engine.speak(f"Admin mode detected. Auto-training {candidate} before execution.")
                from evolution.trainer import software_trainer
                software_trainer.train_skill(candidate)
                self.loader.discover_and_load_skills()
        if app in self.loader.registry and self.loader.registry[app].get("execute"):
            self._narrate("running", app)
            return self.loader.registry[app]["execute"](query=clean)
        launch_skill = self.loader.registry.get("launch_app")
        if launch_skill and launch_skill.get("execute"):
            aliases = getattr(launch_skill.get("module"), "APP_ALIASES", {})
            if candidate in aliases or shutil.which(candidate):
                self._narrate("running", candidate)
                return launch_skill["execute"](target=candidate)
        self.log("AI", "Querying Gemini reasoning engine...")
        plan = self.advisor.plan_task(query)
        if plan.get("success") and plan.get("action") == "launch_app":
            params = plan.get("parameters", {})
            if launch_skill and launch_skill.get("execute"):
                self._narrate("running", params.get("target", "app"))
                return launch_skill["execute"](**params)
        return plan

    def _finalize_task(self, callback, outcome, app):
        self.active_tasks_count = max(0, self.active_tasks_count - 1)
        self._narrate("finish", app, bool(outcome and outcome.get("success")))
        if self.active_tasks_count == 0:
            self.notify_status("Nisa (Admin Mode Active)" if self.admin_mode else "Nisa is ready")
        if callback: callback(outcome)

    def _save_task_record(self, inst, status):
        rid = ObjectId()
        threading.Thread(target=lambda: config.get_collection("tasks").insert_one({"_id": rid, "instruction": inst, "status": status, "created_at": datetime.utcnow().isoformat()}), daemon=True).start()
        return rid

    def _update_task_record(self, rid, status, outcome):
        if rid:
            threading.Thread(target=lambda: config.get_collection("tasks").update_one({"_id": rid}, {"$set": {"status": status, "outcome": outcome, "finished_at": datetime.utcnow().isoformat()}}), daemon=True).start()

orchestration_engine = TaskEngine()
