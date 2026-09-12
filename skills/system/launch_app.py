import os
import shutil
import subprocess
from core.security import security_service

skill_meta = {
    "name": "launch_app",
    "category": "system",
    "version": "1.0.0",
    "description": "Baseline native OS application launcher"
}

APP_ALIASES = {
    "notepad": "notepad.exe",
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "terminal": "wt.exe",
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "code": "code.cmd",
    "taskmgr": "taskmgr.exe",
    "excel": "excel.exe",
    "word": "winword.exe",
    "powerpoint": "powerpnt.exe"
}

def execute(target="", **kwargs):
    if not target or not target.strip():
        return {"success": False, "error": "No target application specified"}

    normalized_target = target.strip()
    executable_name = APP_ALIASES.get(normalized_target.lower(), normalized_target)

    is_safe, message = security_service.is_safe(executable_name)
    if not is_safe:
        return {"success": False, "error": message}

    try:
        if os.path.exists(executable_name):
            os.startfile(executable_name)
            return {"success": True, "target": executable_name, "mode": "direct_path"}

        resolved_in_path = shutil.which(executable_name)
        if resolved_in_path:
            subprocess.Popen([resolved_in_path], shell=True)
            return {"success": True, "target": resolved_in_path, "mode": "path_lookup"}

        subprocess.Popen(f"start {executable_name}", shell=True)
        return {"success": True, "target": executable_name, "mode": "system_start"}
    except Exception as launch_error:
        return {"success": False, "error": str(launch_error)}
