import threading
from datetime import datetime
from core.security import security_service
from core.executor import native_executor
from core.advisor import gemini_advisor
from core.dynamic_loader import skill_loader
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

    def register_log_listener(self, callback):
        self.listeners.append(callback)

    def register_status_listener(self, callback):
        self.status_listeners.append(callback)

    def notify_status(self, status_text):
        for listener in self.status_listeners:
            try:
                listener(status_text)
            except Exception:
                pass

    def log(self, event_type, message):
        for listener in self.listeners:
            try:
                listener(event_type.upper(), message)
            except Exception:
                pass

    def submit_task_async(self, instruction, completion_callback=None):
        worker = threading.Thread(
            target=self._process_task_pipeline,
            args=(instruction, completion_callback),
            daemon=True
        )
        worker.start()

    def _process_task_pipeline(self, raw_instruction, on_finish=None):
        self.active_tasks_count += 1
        self.notify_status("Nisa is executing")
        sanitized = self.security.sanitize(raw_instruction)

        if not sanitized:
            self.log("ERROR", "Received empty task payload")
            self._finalize_task(on_finish, {"status": "rejected"})
            return

        self.log("TASK", f"Processing: {sanitized}")
        task_record_id = self._save_task_record(sanitized, "running")

        result = self._route_instruction(sanitized)
        status_flag = "completed" if result.get("success", False) else "failed"
        self._update_task_record(task_record_id, status_flag, result)

        self.log("DONE" if result.get("success") else "WARN", str(result))
        self._finalize_task(on_finish, result)

    def _route_instruction(self, query):
        lowered = query.lower()
        if lowered.startswith("launch ") or lowered.startswith("open "):
            target_app = query.split(" ", 1)[1].strip()
            launch_skill = self.loader.registry.get("launch_app")
            if launch_skill and launch_skill.get("execute"):
                return launch_skill["execute"](target=target_app)

        self.log("AI", "Querying Gemini reasoning engine...")
        return self.advisor.plan_task(query)

    def _finalize_task(self, callback, outcome):
        self.active_tasks_count = max(0, self.active_tasks_count - 1)
        if self.active_tasks_count == 0:
            self.notify_status("Nisa is ready")
        if callback:
            callback(outcome)

    def _save_task_record(self, instruction, status):
        try:
            col = config.get_collection("tasks")
            doc = {
                "instruction": instruction,
                "status": status,
                "created_at": datetime.utcnow().isoformat()
            }
            res = col.insert_one(doc)
            return res.inserted_id
        except Exception:
            return None

    def _update_task_record(self, record_id, status, outcome):
        if not record_id:
            return
        try:
            col = config.get_collection("tasks")
            col.update_one(
                {"_id": record_id},
                {"$set": {"status": status, "outcome": outcome, "finished_at": datetime.utcnow().isoformat()}}
            )
        except Exception:
            pass

orchestration_engine = TaskEngine()
