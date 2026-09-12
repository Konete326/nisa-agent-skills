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

class TaskEngine:
    def __init__(self):
        self.security = security_service
        self.executor = native_executor
        self.advisor = gemini_advisor
        self.loader = skill_loader
        self.listeners = []
        self.status_listeners = []
        self.active_tasks_count = 0

    def register_log_listener(self, cb):
        self.listeners.append(cb)

    def register_status_listener(self, cb):
        self.status_listeners.append(cb)

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

    def _process_task_pipeline(self, raw_instruction, on_finish=None):
        self.active_tasks_count += 1
        self.notify_status("Nisa is executing")
        sanitized = self.security.sanitize(raw_instruction)
        if not sanitized:
            self.log("ERROR", "Received empty task payload")
            self._finalize_task(on_finish, {"status": "rejected"})
            return
        voice_engine.notify_task_acknowledged(sanitized)
        self.log("TASK", f"Processing: {sanitized}")
        task_record_id = self._save_task_record(sanitized, "running")
        result = self._route_instruction(sanitized)
        status_flag = "completed" if result.get("success", False) else "failed"
        self._update_task_record(task_record_id, status_flag, result)
        self.log("DONE" if result.get("success") else "WARN", str(result))
        self._finalize_task(on_finish, result)

    def _route_instruction(self, query):
        clean, lowered = query.strip(), query.strip().lower()
        if lowered.startswith("train ") or lowered.startswith("learn "):
            from evolution.trainer import software_trainer
            voice_engine.notify_action_executing(f"training {clean}")
            return software_trainer.train_skill(clean)
        if "notepad" in lowered:
            skill = self.loader.registry.get("notepad")
            if skill and skill.get("execute"):
                voice_engine.notify_action_executing("notepad")
                return skill["execute"](query=clean)
        candidate = lowered
        for p in ("launch ", "open "):
            if lowered.startswith(p):
                candidate = lowered[len(p):].strip()
                break
        launch_skill = self.loader.registry.get("launch_app")
        if launch_skill and launch_skill.get("execute"):
            aliases = getattr(launch_skill.get("module"), "APP_ALIASES", {})
            if candidate in aliases or shutil.which(candidate):
                voice_engine.notify_action_executing(candidate)
                return launch_skill["execute"](target=candidate)
        self.log("AI", "Querying Gemini reasoning engine...")
        plan = self.advisor.plan_task(query)
        if plan.get("success") and plan.get("action") == "launch_app":
            params = plan.get("parameters", {})
            if launch_skill and launch_skill.get("execute"):
                voice_engine.notify_action_executing(params.get("target", "app"))
                return launch_skill["execute"](**params)
        return plan

    def _finalize_task(self, callback, outcome):
        self.active_tasks_count = max(0, self.active_tasks_count - 1)
        if self.active_tasks_count == 0:
            self.notify_status("Nisa is ready")
            voice_engine.notify_task_completed(outcome.get("action", "task"))
        if callback: callback(outcome)

    def _save_task_record(self, instruction, status):
        record_id = ObjectId()
        def _write():
            try: config.get_collection("tasks").insert_one({"_id": record_id, "instruction": instruction, "status": status, "created_at": datetime.utcnow().isoformat()})
            except Exception: pass
        threading.Thread(target=_write, daemon=True).start()
        return record_id

    def _update_task_record(self, record_id, status, outcome):
        if not record_id: return
        def _write():
            try: config.get_collection("tasks").update_one({"_id": record_id}, {"$set": {"status": status, "outcome": outcome, "finished_at": datetime.utcnow().isoformat()}})
            except Exception: pass
        threading.Thread(target=_write, daemon=True).start()

orchestration_engine = TaskEngine()
