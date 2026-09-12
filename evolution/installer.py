import shutil
from pathlib import Path
import config
from sync.git_manager import git_gateway

class CodeInstaller:
    def __init__(self):
        self.base_dir = Path(config.BASE_DIR)
        self.staging_dir = self.base_dir / "staging"

    def commit_installation(self, target_relative_path, staged_file):
        try:
            prod_file = self.base_dir / target_relative_path
            shutil.copy2(staged_file, prod_file)
            
            git_gateway.commit_and_push("Nisa autonomous self-upgrade: [feature/fix]")
            self.rollback()
        except Exception:
            self.rollback()

    def rollback(self):
        try:
            if self.staging_dir.exists():
                shutil.rmtree(self.staging_dir, ignore_errors=True)
        except Exception:
            pass

code_installer = CodeInstaller()
