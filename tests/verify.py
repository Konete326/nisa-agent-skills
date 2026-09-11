import ast
import sys
from pathlib import Path

MAX_LINE_LIMIT = 120
PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRECTORIES = {".venv", "__pycache__", ".git", "dist", "build"}

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def audit_codebase():
    overall_success = True
    checked_files_count = 0

    print("=" * 64)
    print(f"{'FILE':<38} | {'LINES':<7} | {'SYNTAX':<8} | {'STATUS'}")
    print("=" * 64)

    for python_file in sorted(PROJECT_ROOT.rglob("*.py")):
        if any(excluded in python_file.parts for excluded in EXCLUDED_DIRECTORIES):
            continue

        relative_name = python_file.relative_to(PROJECT_ROOT).as_posix()
        checked_files_count += 1
        source_content = python_file.read_text(encoding="utf-8")
        line_count = len(source_content.splitlines())

        syntax_valid = True
        try:
            ast.parse(source_content, filename=str(python_file))
        except SyntaxError as syntax_err:
            syntax_valid = False
            print(f"[ERROR {relative_name}]: {syntax_err}")

        line_count_valid = line_count <= MAX_LINE_LIMIT
        file_passed = syntax_valid and line_count_valid
        if not file_passed:
            overall_success = False

        status_text = "PASS" if file_passed else "FAIL"
        syntax_text = "OK" if syntax_valid else "ERR"
        print(f"{relative_name:<38} | {line_count:<7} | {syntax_text:<8} | {status_text}")

    print("=" * 64)

    try:
        from core.dynamic_loader import skill_loader
        loader_valid, failed_skills = skill_loader.dry_run_check()
        if not loader_valid:
            overall_success = False
            print(f"[SKILL LOADER FAIL]: Failed loading skills {failed_skills}")
        else:
            print("[SKILL LOADER]: Dry-run check passed successfully.")
    except Exception as loader_err:
        overall_success = False
        print(f"[SKILL LOADER EXCEPTION]: {loader_err}")

    if overall_success and checked_files_count > 0:
        print(f"[VERIFY SUCCESS]: {checked_files_count} files verified <= {MAX_LINE_LIMIT} lines.")
        return 0
    print("[VERIFY FAILED]: One or more verification checks failed.")
    return 1

if __name__ == "__main__":
    sys.exit(audit_codebase())
