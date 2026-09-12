import shutil
import subprocess
import sys
from pathlib import Path
import config
from evolution.installer import code_installer

class CodeMutator:
    def __init__(self):
        self.base_dir = Path(config.BASE_DIR)
        self.staging_dir = self.base_dir / "staging"
        self.verify_script = self.base_dir / "tests" / "verify.py"

    def stage_mutation(self, target_relative_path, new_code):
        try:
            self._prepare_staging()
            staged_file = self.staging_dir / target_relative_path
            staged_file.parent.mkdir(parents=True, exist_ok=True)
            
            staged_file.write_text(new_code, encoding="utf-8")
            
            is_valid = self._verify_staging()
            if is_valid:
                code_installer.commit_installation(target_relative_path, staged_file)
            else:
                code_installer.rollback()
        except Exception:
            code_installer.rollback()

    def _prepare_staging(self):
        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir, ignore_errors=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

    def _verify_staging(self):
        try:
            result = subprocess.run(
                [sys.executable, str(self.verify_script)],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

code_mutator = CodeMutator()
