import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from evolution.critic import system_critic
from evolution.installer import code_installer
from sync.git_manager import git_gateway

class MockResponse:
    def __init__(self, text):
        self.text = text

class MockModel:
    def generate_content(self, model, contents):
        return MockResponse("def dummy_func():\n    return True\n")

class MockClient:
    def __init__(self):
        self.models = MockModel()

def run_test():
    original_commit = git_gateway.commit_and_push
    git_gateway.commit_and_push = lambda msg: {"success": True, "message": "Mocked"}
    
    test_file_path = Path(config.BASE_DIR) / "ui" / "dummy_test.py"
    try:
        dummy_code = "def dummy_func():\n    pass\n"
        test_file_path.write_text(dummy_code, encoding="utf-8")
        
        bottlenecks = system_critic.scan_for_bottlenecks()
        target_issue = None
        for b in bottlenecks:
            if b.get("target_file") == "ui/dummy_test.py":
                target_issue = b
                break
                
        if not target_issue:
            print("[TEST FAILED] Critic did not detect the dummy issue.")
            return 1
            
        print("[TEST PASS] Critic detected issue.")
        
        from evolution.scout import evolution_scout
        evolution_scout.client = MockClient()
        evolution_scout._handle_prompt(json.dumps(target_issue))
        
        swapped_code = test_file_path.read_text(encoding="utf-8")
        if "return True" in swapped_code:
            print("[TEST PASS] Cycle completed successfully.")
        else:
            print("[TEST FAILED] Hot-swap failed.")
            return 1
            
        return 0
    finally:
        if test_file_path.exists():
            test_file_path.unlink()
        code_installer.rollback()
        git_gateway.commit_and_push = original_commit

if __name__ == "__main__":
    sys.exit(run_test())
