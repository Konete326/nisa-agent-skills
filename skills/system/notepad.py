import os
import time
import subprocess
from pathlib import Path
from pywinauto import Desktop

SKILL_METADATA = {
    "name": "notepad",
    "version": "3.0.0",
    "actions": ["launch", "write", "save", "read"]
}
skill_meta = SKILL_METADATA

def _get_notepad_edit():
    d = Desktop(backend="uia")
    try:
        np = d.window(class_name="Notepad")
        edit = np.child_window(class_name="Edit")
        edit.iface_value
        return np, edit
    except Exception:
        try:
            np = d.window(class_name="Notepad")
            edit = np.child_window(control_type="Document")
            edit.iface_value
            return np, edit
        except Exception:
            subprocess.Popen("notepad.exe")
            time.sleep(1.0)
            np = d.window(class_name="Notepad")
            try:
                return np, np.child_window(class_name="Edit")
            except Exception:
                return np, np.child_window(control_type="Document")

def launch(**kwargs):
    try:
        np, _ = _get_notepad_edit()
        try:
            np.set_focus()
        except Exception:
            pass
        return {"success": True, "action": "launch", "message": "Notepad active"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def write(text="", append=False, **kwargs):
    try:
        _, edit = _get_notepad_edit()
        current = edit.iface_value.CurrentValue or ""
        new_val = (current + "\n" + str(text)) if append and current else str(text)
        edit.iface_value.SetValue(new_val)
        return {"success": True, "action": "write", "length": len(new_val)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def read(**kwargs):
    try:
        _, edit = _get_notepad_edit()
        return {"success": True, "action": "read", "content": edit.iface_value.CurrentValue or ""}
    except Exception as e:
        return {"success": False, "error": str(e)}

def save(file_path=None, target=None, **kwargs):
    try:
        _, edit = _get_notepad_edit()
        content = edit.iface_value.CurrentValue or ""
        raw_path = file_path or target or "notes.txt"
        desktop_dir = Path.home() / "Desktop"
        if "desktop" in str(raw_path).lower():
            fname = Path(raw_path).name
            if fname.lower() == "desktop" or not fname:
                fname = "notes.txt"
            resolved_path = desktop_dir / fname
        else:
            resolved_path = Path(raw_path).resolve()
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(content, encoding="utf-8")
        return {"success": True, "action": "save", "path": str(resolved_path)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def execute(action="launch", query="", **kwargs):
    if query:
        lowered = query.lower()
        if not any(k in lowered for k in ("write", "type", "save", "read")):
            return launch(**kwargs)
        if "read" in lowered and not ("write" in lowered or "type" in lowered):
            return read(**kwargs)
        text_val, save_target = "", ""
        if "write " in lowered or "type " in lowered:
            kw = "write " if "write " in lowered else "type "
            seg = query[query.lower().find(kw) + len(kw):]
            for sep in (" in notepad", " to notepad", " into notepad"):
                if sep in seg.lower():
                    text_val = seg[:seg.lower().find(sep)].strip().strip('"\'')
                    break
            if not text_val:
                text_val = seg.split(" and save")[0].strip().strip('"\'')
        if "save" in lowered:
            for kw in ("save to ", "save as ", "save in "):
                if kw in lowered:
                    save_target = query[query.lower().find(kw) + len(kw):].strip()
                    break
            save_target = save_target or "notes.txt"
        res = write(text=text_val or "Hello from Nisa")
        if save_target:
            save_res = save(file_path=save_target)
            return {"success": True, "action": "write_and_save", "details": save_res}
        return res
    routes = {"launch": launch, "write": write, "read": read, "save": save}
    return routes.get(action.lower(), launch)(**kwargs)