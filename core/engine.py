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
    def notify_status(self, text): [l(text) for l in self.status_listeners]
    def log(self, cat, msg): [l(cat.upper(), msg) for l in self.listeners]

    def submit_task_async(self, instruction, completion_callback=None):
        threading.Thread(target=self._process_task_pipeline, args=(instruction, completion_callback), daemon=True).start()

    def _identify_target(self, q):
        return next((a for a in ("notepad", "excel", "chrome", "calc", "word", "powerpoint", "cmd", "terminal") if a in q.lower()), None)

    def _narrate(self, stage, app, ok=True):
        st = stage if stage != "finish" else ("done" if ok else "fail")
        lang = getattr(voice_engine, "get_language", lambda: "UR")()
        voice_engine.speak(STAGE_MSGS.get(st, {}).get(lang, STAGE_MSGS[st]["UR"]).format(app.capitalize() if app else "Task"))

    def _process_task_pipeline(self, raw, on_finish=None):
        self.active_tasks_count += 1; self.notify_status("Nisa is executing")
        san = self.security.sanitize(raw); target_app = self._identify_target(san or "")
        if not san:
            self.log("ERROR", "Received empty task payload"); self._finalize_task(on_finish, {"success": False, "status": "rejected"}, target_app); return
        self._narrate("start", target_app); self.log("TASK", f"Processing: {san}")
        rid = self._save_task_record(san, "running")
        try: result = self._route_instruction(san, target_app)
        except Exception as err: self.log("ERROR", f"Task crash: {err}"); result = {"success": False, "error": str(err)}
        ok = bool(result and (result.get("success") or result.get("status") == "success"))
        self._update_task_record(rid, "completed" if ok else "failed", result)
        self.log("DONE" if ok else "WARN", str(result)); self._finalize_task(on_finish, result, target_app)

    def _is_gap(self, res, q):
        if not res or res.get("success") is False or res.get("status") == "error": return True
        s = str(res).lower()
        if "unknown action" in s or (any(w in q.lower() for w in ("table", "write", "likho")) and ("launched" in s or res.get("action") == "launch")): return True
        return bool(res.get("steps") and any(st.get("status") == "error" or "unknown" in str(st).lower() for st in res["steps"]))

    def _route_instruction(self, query, app):
        clean, lowered = query.strip(), query.strip().lower()
        if lowered.startswith("train ") or lowered.startswith("learn "):
            from evolution.trainer import software_trainer
            return software_trainer.train_skill(clean)
        candidate = app or lowered.replace("launch ", "").replace("open ", "").strip()
        result = None
        try:
            if app and any(v in lowered for v in ("likho", "write", "save", "jama", "type", "table")):
                plan = self.advisor.plan_task(clean)
                steps, sk = plan.get("steps", []), self.loader.registry.get(app or plan.get("target"))
                if sk and sk.get("execute"):
                    voice_engine.speak("Text likh kar save kar rahi hoon")
                    if steps: result = {"success": True, "action": "multi_step", "steps": [sk["execute"](action=st.get("action", "launch"), **{k: v for k, v in st.items() if k != "action"}) for st in steps]}
                    else: result = sk["execute"](query=clean)
            elif app in self.loader.registry and self.loader.registry[app].get("execute"):
                self._narrate("running", app); result = self.loader.registry[app]["execute"](query=clean)
            else:
                lsk = self.loader.registry.get("launch_app")
                if lsk and lsk.get("execute") and (candidate in getattr(lsk.get("module"), "APP_ALIASES", {}) or shutil.which(candidate)):
                    self._narrate("running", candidate); result = lsk["execute"](target=candidate)
                else:
                    self.log("AI", "Querying Gemini reasoning engine...")
                    plan = self.advisor.plan_task(query)
                    if plan.get("success") and plan.get("action") == "launch_app" and lsk and lsk.get("execute"):
                        p = plan.get("parameters", {}); self._narrate("running", p.get("target", "app")); result = lsk["execute"](**p)
                    else: result = plan
        except Exception as ex: result = {"success": False, "status": "error", "error": str(ex)}

        if self.admin_mode and self._is_gap(result, clean):
            target = candidate or app or "system"
            self.log("EVOLVE", f"Admin Mode: Auto-evolving capability for '{clean}'")
            voice_engine.speak(f"{target.capitalize()} ki nayi skill seekh kar update kar rahi hoon")
            from evolution.trainer import software_trainer
            if software_trainer.evolve_skill_for_task(target, clean).get("success"):
                self.loader.discover_and_load_skills()
                voice_engine.speak("Skill update ho gayi, task execute kar rahi hoon")
                sk = self.loader.registry.get(target)
                if sk and sk.get("execute"):
                    res = sk["execute"](query=clean)
                    return sk["execute"](action="table", query=clean) if (not res or res.get("status") == "error") and "table" in clean.lower() else res
        return result

    def _finalize_task(self, cb, outcome, app):
        self.active_tasks_count = max(0, self.active_tasks_count - 1)
        ok = bool(outcome and (outcome.get("success") or outcome.get("status") == "success"))
        self._narrate("finish", app, ok)
        if self.active_tasks_count == 0: self.notify_status("Nisa (Admin Mode Active)" if self.admin_mode else "Nisa is ready")
        if cb: cb(outcome)

    def _save_task_record(self, inst, status):
        rid = ObjectId()
        threading.Thread(target=lambda: config.get_collection("tasks").insert_one({"_id": rid, "instruction": inst, "status": status, "created_at": datetime.utcnow().isoformat()}), daemon=True).start()
        return rid

    def _update_task_record(self, rid, status, outcome):
        if rid: threading.Thread(target=lambda: config.get_collection("tasks").update_one({"_id": rid}, {"$set": {"status": status, "outcome": outcome, "finished_at": datetime.utcnow().isoformat()}}), daemon=True).start()

orchestration_engine = TaskEngine()
