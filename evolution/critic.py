import os
from pathlib import Path
import json
import config

class CodebaseCritic:
    def __init__(self):
        self.base_dir = Path(config.BASE_DIR)
        self.target_dirs = [self.base_dir / "ui", self.base_dir / "core"]
        self.line_warning_threshold = 110
        self.max_lines = 120

    def scan_for_bottlenecks(self):
        bottlenecks = []
        for target_dir in self.target_dirs:
            if not target_dir.exists():
                continue
            for py_file in target_dir.rglob("*.py"):
                if py_file.name == "__init__.py":
                    continue
                issue = self._analyze_file(py_file)
                if issue:
                    bottlenecks.append(issue)
        return bottlenecks

    def _analyze_file(self, file_path):
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            line_count = len(lines)
            
            if line_count >= self.line_warning_threshold:
                return {
                    "target_file": file_path.relative_to(self.base_dir).as_posix(),
                    "issue": f"Approaching line limit ({line_count}/{self.max_lines})",
                    "optimization_goal": "Refactor logic to reduce line count safely without comments."
                }
            
            if "TODO" in content or "pass" in content:
                return {
                    "target_file": file_path.relative_to(self.base_dir).as_posix(),
                    "issue": "Contains incomplete logic or stubs",
                    "optimization_goal": "Complete the stubbed logic and ensure dynamic flexibility."
                }
        except Exception:
            pass
        return None

    def formulate_prompts(self):
        bottlenecks = self.scan_for_bottlenecks()
        return [json.dumps(b) for b in bottlenecks]

system_critic = CodebaseCritic()
