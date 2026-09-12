import sys
import ast
import shutil
import subprocess
from pathlib import Path
from google import genai
from google.genai import types
import config
from sync.git_manager import git_gateway

class DocstringRemover(ast.NodeTransformer):
    def _strip(self, body):
        return body[1:] if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str)) else body
    def visit_Module(self, n): self.generic_visit(n); n.body = self._strip(n.body); return n
    def visit_ClassDef(self, n): self.generic_visit(n); n.body = self._strip(n.body); return n
    def visit_FunctionDef(self, n): self.generic_visit(n); n.body = self._strip(n.body); return n
    def visit_AsyncFunctionDef(self, n): self.generic_visit(n); n.body = self._strip(n.body); return n

class SoftwareTrainer:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.candidate_models = ("gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest")
        self.base_dir = Path(config.BASE_DIR)
        self.staging_dir = self.base_dir / "staging"
        self.verify_script = self.base_dir / "tests" / "verify.py"
        self.client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=25000)) if self.api_key else None

    def train_skill(self, software_name):
        clean = software_name.lower().replace("train ", "").replace("learn ", "").strip()
        target_path = self.base_dir / "skills" / "system" / f"{clean}.py"
        existing = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        current_ver = self._extract_version(existing)
        next_ver = self._increment_version(current_ver)

        code = self._generate_skill_code(clean, next_ver, existing)
        if not code or not self._validate_code(code):
            code = self._repair_code(clean, next_ver, code or existing)
            if not code or not self._validate_code(code):
                return {"success": False, "error": "Code generation failed"}

        staged = self.staging_dir / "skills" / "system" / f"{clean}.py"
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text(code, encoding="utf-8")

        if self._verify_staging():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staged, target_path)
            shutil.rmtree(self.staging_dir, ignore_errors=True)
            git_gateway.commit_and_push(f"Nisa Skill Upgrade: {clean} v{next_ver}")
            return {"success": True, "skill": clean, "version": next_ver}

        shutil.rmtree(self.staging_dir, ignore_errors=True)
        return {"success": False, "error": "Staged verification failed"}

    def _query_models(self, prompt):
        if not self.client: return None
        for m in self.candidate_models:
            try:
                res = self.client.models.generate_content(model=m, contents=prompt)
                if res and res.text: return self._clean_code(res.text)
            except Exception: pass
        return None

    def _generate_skill_code(self, name, version, existing):
        prompt = (
            f"Generate a native Python skill file for Windows app '{name}'. "
            f"VERSION: {version}. EXISTING: {existing}. "
            "RULES: STRICTLY ZERO COMMENTS, ZERO DOCSTRINGS, line count <= 110 lines. "
            f"Must define SKILL_METADATA = {{'name': '{name}', 'version': '{version}', 'actions': ['launch', 'write', 'save', 'read']}}. "
            "Must define execute(action='launch', **kwargs). Return raw executable Python code only, no markdown."
        )
        return self._query_models(prompt)

    def _repair_code(self, name, version, invalid_code):
        prompt = f"Fix syntax errors, strip docstrings, <= 110 lines. Version '{version}':\\n{invalid_code}"
        return self._query_models(prompt)

    def _clean_code(self, raw_text):
        text = raw_text.strip()
        if "```python" in text: text = text.split("```python", 1)[1]
        elif "```" in text: text = text.split("```", 1)[1]
        if "```" in text: text = text.split("```", 1)[0]
        cleaned = "\n".join(l for l in text.strip().splitlines() if not l.strip().startswith("#"))
        try:
            tree = ast.parse(cleaned)
            tree = DocstringRemover().visit(tree)
            ast.fix_missing_locations(tree)
            return ast.unparse(tree).strip()
        except Exception:
            return cleaned.strip()

    def _validate_code(self, code):
        if not code or len(code.splitlines()) > 120: return False
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if ast.get_docstring(node): return False
            return not any("#" in l for l in code.splitlines())
        except Exception: return False

    def _extract_version(self, code):
        for line in code.splitlines():
            if '"version":' in line or "'version':" in line:
                return line.split(":")[1].replace('"', '').replace("'", "").replace(",", "").strip()
        return "1.0.0"

    def _increment_version(self, ver):
        try: return f"{int(ver.split('.')[0]) + 1}.0.0"
        except Exception: return "2.0.0"

    def _verify_staging(self):
        try: return subprocess.run([sys.executable, str(self.verify_script)], cwd=str(self.base_dir), capture_output=True, text=True).returncode == 0
        except Exception: return False

software_trainer = SoftwareTrainer()
