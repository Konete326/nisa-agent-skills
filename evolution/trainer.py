import sys
import json
import shutil
import subprocess
from pathlib import Path
from google import genai
from google.genai import types
import config
from sync.git_manager import git_gateway

class SoftwareTrainer:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.model_id = "gemini-3.6-flash"
        self.base_dir = Path(config.BASE_DIR)
        self.staging_dir = self.base_dir / "staging"
        self.verify_script = self.base_dir / "tests" / "verify.py"
        opts = types.HttpOptions(timeout=4000, headers={"X-Server-Timeout": "10"})
        self.client = genai.Client(api_key=self.api_key, http_options=opts) if self.api_key else None

    def train_skill(self, software_name):
        clean_name = software_name.lower().replace("train ", "").replace("learn ", "").strip()
        target_path = self.base_dir / "skills" / "system" / f"{clean_name}.py"
        existing_code = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        current_version = self._extract_version(existing_code)
        next_version = self._increment_version(current_version)

        capability_matrix = self._query_capabilities(clean_name)
        new_code = self._generate_skill_code(clean_name, next_version, capability_matrix, existing_code)
        if not new_code:
            return {"success": False, "error": "Code generation failed"}

        staged_path = self.staging_dir / "skills" / "system" / f"{clean_name}.py"
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        staged_path.write_text(new_code, encoding="utf-8")

        if self._verify_staging(clean_name):
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staged_path, target_path)
            shutil.rmtree(self.staging_dir, ignore_errors=True)
            msg = f"Nisa Skill Upgrade: {clean_name} v{next_version}"
            git_gateway.commit_and_push(msg)
            return {"success": True, "skill": clean_name, "version": next_version}

        shutil.rmtree(self.staging_dir, ignore_errors=True)
        return {"success": False, "error": "Staged verification failed"}

    def _query_capabilities(self, name):
        if not self.client:
            return "Standard desktop application controls"
        prompt = f"Provide a concise capability matrix (shortcuts, UI tree, menus, CLI switches) for {name} on Windows."
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=prompt)
            return res.text.strip() if res and res.text else ""
        except Exception:
            return "Basic capability matrix"

    def _generate_skill_code(self, name, version, matrix, existing):
        if not self.client:
            return existing
        prompt = (
            f"Generate a complete native Python skill file for '{name}'. "
            f"VERSION: {version}. CAPABILITIES: {matrix}. "
            f"EXISTING: {existing}. "
            "RULES: STRICTLY NO COMMENTS, NO DOCSTRINGS, <= 110 lines. "
            "MUST define SKILL_METADATA = {'name': '...','version': '...','actions': [...]}. "
            "MUST define execute(action, **kwargs). Output ONLY raw Python code."
        )
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=prompt)
            code = res.text.strip() if res and res.text else ""
            if code.startswith("```python"):
                code = code[9:]
            if code.endswith("```"):
                code = code[:-3]
            return code.strip()
        except Exception:
            return None

    def _extract_version(self, code):
        for line in code.splitlines():
            if '"version":' in line or "'version':" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    return parts[1].replace('"', '').replace("'", "").replace(",", "").strip()
        return "1.0.0"

    def _increment_version(self, ver):
        try:
            major = int(ver.split(".")[0])
            return f"{major + 1}.0.0"
        except Exception:
            return "2.0.0"

    def _verify_staging(self, name):
        try:
            res = subprocess.run([sys.executable, str(self.verify_script)], cwd=str(self.base_dir), capture_output=True, text=True)
            return res.returncode == 0
        except Exception:
            return False

software_trainer = SoftwareTrainer()
