import sys
import importlib.util
from pathlib import Path
import config

class SkillHotLoader:
    def __init__(self, root_directory=None):
        self.root_directory = root_directory or config.SKILLS_DIR
        self.registry = {}
        self.discover_and_load_skills()

    def discover_and_load_skills(self):
        if not self.root_directory.exists():
            return self.registry

        for script_path in self.root_directory.rglob("*.py"):
            if script_path.name.startswith("__"):
                continue
            self.load_single_skill(script_path)
        return self.registry

    def load_single_skill(self, file_path):
        module_identifier = f"nisa_skill_{file_path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_identifier, str(file_path))
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_identifier] = module
            spec.loader.exec_module(module)

            meta_data = getattr(module, "skill_meta", {
                "name": file_path.stem,
                "description": "Native Nisa skill"
            })
            entry = {
                "name": file_path.stem,
                "category": file_path.parent.name,
                "file_path": str(file_path),
                "module": module,
                "metadata": meta_data,
                "execute": getattr(module, "execute", None)
            }
            self.registry[file_path.stem] = entry
            return entry
        except Exception:
            return None

    def reload_skill(self, skill_name):
        if skill_name in self.registry:
            target_path = Path(self.registry[skill_name]["file_path"])
            return self.load_single_skill(target_path) is not None
        return False

    def dry_run_check(self):
        failed_skills = []
        for script_path in self.root_directory.rglob("*.py"):
            if script_path.name.startswith("__"):
                continue
            result = self.load_single_skill(script_path)
            if not result or not callable(result.get("execute")):
                failed_skills.append(str(script_path))
        return len(failed_skills) == 0, failed_skills

skill_loader = SkillHotLoader()
