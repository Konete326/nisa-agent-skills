import os
import time
import subprocess
from pathlib import Path
import win32gui
from pywinauto import Desktop

SKILL_METADATA = {
    "name": "notepad",
    "version": "3.0.0",
    "actions": ["launch", "write", "save", "read"]
}
skill_meta = SKILL_METADATA

def _find_notepad_hwnd():
    hwnd = win32gui.FindWindow("Notepad", None)
    if not hwnd:
        hwnds = []
        def _cb(h, l):
            if "notepad" in win32gui.GetWindowText(h).lower(): l.append(h)
        win32gui.EnumWindows(_cb, hwnds)
        if hwnds: hwnd = hwnds[0]
    return hwnd

def _get_notepad_edit():
    hwnd = _find_notepad_hwnd()
    if not hwnd:
        subprocess.Popen("notepad.exe")
        time.sleep(1.0)
        hwnd = _find_notepad_hwnd()
    else:
        try:
            win32gui.ShowWindow(hwnd, 9)
            win32gui.SetForegroundWindow(hwnd)
        except Exception: pass
    d = Desktop(backend="uia")
    np = d.window(handle=hwnd) if hwnd else d.window(class_name="Notepad")
    try:
        edit = np.child_window(class_name="Edit")
        edit.iface_value
        return np, edit
    except Exception:
        edit = np.child_window(control_type="Document")
        edit.iface_value
        return np, edit

def launch(**kwargs):
    try:
        np, _ = _get_notepad_edit()
        try: np.set_focus()
        except Exception: pass
        return {"success": True, "action": "launch", "message": "Notepad active"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def write(text="", append=False, **kwargs):
    try:
        _, edit = _get_notepad_edit()
        cur = edit.iface_value.CurrentValue or ""
        new_val = (cur + "\n" + str(text)) if append and cur else str(text)
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

def save(file_path=None, target=None, path=None, **kwargs):
    try:
        _, edit = _get_notepad_edit()
        content = edit.iface_value.CurrentValue or ""
        raw = file_path or target or path or "notes.txt"
        desktop = Path.home() / "Desktop"
        fname = Path(raw).name if raw != "default" else "notes.txt"
        resolved = desktop / (fname or "notes.txt") if "desktop" in str(raw).lower() or raw == "default" else Path(raw).resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return {"success": True, "action": "save", "path": str(resolved)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def execute(action="launch", query="", **kwargs):
    if query:
        low = query.lower()
        if not any(k in low for k in ("write", "type", "likho", "save", "read")):
            return launch(**kwargs)
        if "read" in low and not any(k in low for k in ("write", "type", "likho")):
            return read(**kwargs)
        text_val, save_target = "", ""
        for kw in ("write ", "type ", "likho "):
            if kw in low:
                seg = query[query.lower().find(kw) + len(kw):]
                for sep in (" in notepad", " to notepad", " pe ", " par "):
                    if sep in seg.lower():
                        text_val = seg[:seg.lower().find(sep)].strip().strip('"\'')
                        break
                if not text_val:
                    text_val = seg.split(" and save")[0].split(" aur save")[0].strip().strip('"\'')
                break
        res = write(text=text_val or "hello world")
        if "save" in low:
            save_res = save(file_path="notes.txt")
            return {"success": True, "action": "write_and_save", "details": save_res}
        return res
    routes = {"launch": launch, "focus_or_launch": launch, "write": write, "read": read, "save": save}
    res = routes.get(action.lower(), launch)(**kwargs)
    if "text" in kwargs and action.lower() not in ("write", "read"):
        write(text=kwargs["text"])
    if ("save_path" in kwargs or "file_path" in kwargs or "path" in kwargs) and action.lower() != "save":
        save(file_path=kwargs.get("save_path") or kwargs.get("file_path") or kwargs.get("path"))
    return res