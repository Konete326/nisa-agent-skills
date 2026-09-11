import os
import platform
import subprocess
import pyautogui
from core.security import security_service

class NativeExecutor:
    def __init__(self, validator=security_service):
        self.validator = validator
        pyautogui.FAILSAFE = True

    def run_system_command(self, command_line, timeout_seconds=30):
        is_safe, message = self.validator.is_safe(command_line)
        if not is_safe:
            return {"success": False, "stdout": "", "stderr": message, "exit_code": -1}

        is_windows = platform.system() == "Windows"
        try:
            completed = subprocess.run(
                command_line,
                shell=is_windows,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            return {
                "success": completed.returncode == 0,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
                "exit_code": completed.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "Execution timed out", "exit_code": -2}
        except Exception as error:
            return {"success": False, "stdout": "", "stderr": str(error), "exit_code": -3}

    def launch_executable(self, target_path):
        is_safe, message = self.validator.is_safe(target_path)
        if not is_safe:
            return {"success": False, "message": message}

        try:
            if platform.system() == "Windows" and os.path.exists(target_path):
                os.startfile(target_path)
            else:
                subprocess.Popen(target_path, shell=True)
            return {"success": True, "message": f"Successfully launched {target_path}"}
        except Exception as error:
            return {"success": False, "message": str(error)}

    def automate_mouse_click(self, x_pos, y_pos):
        try:
            pyautogui.click(x=x_pos, y=y_pos)
            return {"success": True, "message": f"Clicked at ({x_pos}, {y_pos})"}
        except Exception as error:
            return {"success": False, "message": str(error)}

    def automate_text_entry(self, input_text):
        try:
            pyautogui.write(input_text, interval=0.02)
            return {"success": True, "message": "Text typed successfully"}
        except Exception as error:
            return {"success": False, "message": str(error)}

native_executor = NativeExecutor()
