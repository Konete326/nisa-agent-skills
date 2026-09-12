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
    def generic_visit(self, n):
        super().generic_visit(n)
        if getattr(n, "body", None) and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant) and isinstance(n.body[0].value.value, str): n.body = n.body[1:]
        return n

class SoftwareTrainer:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.candidate_models = ("gemini-flash-lite-latest", "gemini-flash-latest", "gemini-3.5-flash")
        self.base_dir = Path(config.BASE_DIR)
        self.staging_dir = self.base_dir / "staging"
        self.verify_script = self.base_dir / "tests" / "verify.py"
        self.client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=25000)) if self.api_key else None

    def train_skill(self, software_name):
        clean = software_name.lower().replace("train ", "").replace("learn ", "").strip()
        target = self.base_dir / "skills" / "system" / f"{clean}.py"
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        ver = self._increment_version(self._extract_version(existing))
        code = self._generate_skill_code(clean, ver, existing)
        if not code or not self._validate_code(code): code = self._repair_code(clean, ver, code or existing)
        if not code or not self._validate_code(code): return {"success": False, "error": "Code gen failed"}
        return self._deploy(clean, code, f"Nisa Skill Upgrade: {clean} v{ver}", {"success": True, "skill": clean, "version": ver})

    def evolve_skill_for_task(self, app_name, task_instruction):
        clean = app_name.lower().replace("launch ", "").replace("open ", "").strip()
        target = self.base_dir / "skills" / "system" / f"{clean}.py"
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        prompt = (
            f"Update existing Python skill for '{clean}' to support: '{task_instruction}'. "
            "Rules: Return raw executable Python code only. STRICTLY 0 comments, 0 docstrings, <= 110 lines. "
            "Must keep existing actions and append/merge the required new capability. "
            "Ensure execute(action='launch', **kwargs) handles action=='table' or 'table' in str(kwargs.get('query', '')).lower() "
            "by writing math table into active Excel worksheet cells. "
            f"Existing Code:\n{existing}"
        )
        code = self._query_models(prompt)
        if not code or not self._validate_code(code): code = self._repair_code(clean, "2.1.0", code or existing)
        if not code or not self._validate_code(code):
            if clean == "excel" and "table" in task_instruction.lower(): code = self._inject_excel_table(existing)
            else: return {"success": False, "error": "Evolution gen failed"}
        return self._deploy(clean, code, f"Nisa Auto-Evolve: {clean} for task '{task_instruction}'", {"success": True, "app": clean})

    def _inject_excel_table(self, ex):
        inj = "    q = kwargs.get('query', '')\n    if action == 'table' or 'table' in str(q).lower():\n        try:\n            wb = excel.ActiveWorkbook or excel.Workbooks.Add()\n            for i in range(1, 11): wb.ActiveSheet.Cells(i, 1).Value, wb.ActiveSheet.Cells(i, 2).Value = f'2 x {i}', 2 * i\n            return {'status': 'success', 'message': 'Table generated'}\n        except Exception as e: return {'status': 'error', 'message': str(e)}\n"
        return ex.replace("excel = get_excel()\n", f"excel = get_excel()\n{inj}", 1) if "excel = get_excel()" in ex else ex

    def _deploy(self, clean, code, msg, ret):
        staged = self.staging_dir / "skills" / "system" / f"{clean}.py"
        staged.parent.mkdir(parents=True, exist_ok=True); staged.write_text(code, encoding="utf-8")
        target = self.base_dir / "skills" / "system" / f"{clean}.py"
        ok = self._verify_staging()
        if ok: shutil.copy2(staged, target); git_gateway.commit_and_push(msg)
        shutil.rmtree(self.staging_dir, ignore_errors=True)
        return ret if ok else {"success": False, "error": "Staged verification failed"}

    def _query_models(self, prompt):
        if not self.client: return None
        for m in self.candidate_models:
            try:
                res = self.client.models.generate_content(model=m, contents=prompt)
                if res and res.text: return self._clean_code(res.text)
            except Exception: pass
        return None

    def _generate_skill_code(self, name, version, existing):
        prompt = f"Generate native Python skill for Windows app '{name}'. V{version}. Existing:\n{existing}\nRULES: 0 comments, 0 docstrings, <=110 lines. Must define SKILL_METADATA and execute(action='launch', **kwargs). Output code only."
        return self._query_models(prompt)

    def _repair_code(self, name, version, invalid_code):
        return self._query_models(f"Fix syntax errors, strip docstrings, <= 110 lines. Version '{version}':\n{invalid_code}")

    def _clean_code(self, raw_text):
        text = raw_text.strip()
        for fence in ("```python", "```"):
            if fence in text: text = text.split(fence, 1)[1]
        if "```" in text: text = text.split("```", 1)[0]
        cleaned = "\n".join(l for l in text.strip().splitlines() if not l.strip().startswith("#"))
        try:
            tree = ast.parse(cleaned); DocstringRemover().visit(tree); ast.fix_missing_locations(tree)
            return ast.unparse(tree).strip()
        except Exception: return cleaned.strip()

    def _validate_code(self, code):
        if not code or len(code.splitlines()) > 120: return False
        try:
            tree = ast.parse(code)
            has_doc = any(ast.get_docstring(n) for n in ast.walk(tree) if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)))
            return not has_doc and not any("#" in l for l in code.splitlines())
        except Exception: return False

    def _extract_version(self, code):
        return next((l.split(":")[1].replace('"', '').replace("'", "").replace(",", "").strip() for l in code.splitlines() if "version" in l and ":" in l), "1.0.0")

    def _increment_version(self, ver): return f"{int(ver.split('.')[0]) + 1}.0.0" if ver else "2.0.0"

    def _verify_staging(self):
        try: return subprocess.run([sys.executable, str(self.verify_script)], cwd=str(self.base_dir), capture_output=True, text=True).returncode == 0
        except Exception: return False

software_trainer = SoftwareTrainer()
