import subprocess
import sys
from pathlib import Path
import git
import config

class SafeGitGateway:
    def __init__(self, repo_path=None):
        self.repo_path = Path(repo_path or config.BASE_DIR)
        self.verify_script = self.repo_path / "tests" / "verify.py"

    def run_self_verification(self):
        result = subprocess.run(
            [sys.executable, str(self.verify_script)],
            cwd=str(self.repo_path),
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout + result.stderr

    def commit_and_push(self, commit_message="Update autonomous skills"):
        passed_verify, output_log = self.run_self_verification()
        if not passed_verify:
            return {
                "success": False,
                "message": "Zero-push gateway blocked push: Self-verification failed.",
                "details": output_log
            }

        try:
            repo = git.Repo(self.repo_path)
            repo.git.add(all=True)

            if repo.is_dirty(untracked_files=True):
                repo.index.commit(commit_message)

            if not config.GITHUB_TOKEN or not config.GITHUB_SKILLS_REPO:
                return {
                    "success": True,
                    "message": "Committed locally. Remote push skipped (credentials not configured)."
                }

            origin_url = f"https://{config.GITHUB_TOKEN}@github.com/{config.GITHUB_SKILLS_REPO}.git"
            if "origin" in [remote.name for remote in repo.remotes]:
                repo.remotes.origin.set_url(origin_url)
            else:
                repo.create_remote("origin", origin_url)

            current_branch = repo.active_branch.name
            repo.git.push("-u", "origin", current_branch, "--force")
            return {"success": True, "message": f"Verified and pushed branch '{current_branch}' to {config.GITHUB_SKILLS_REPO}."}
        except Exception as git_error:
            return {"success": False, "message": f"Git operation failed: {str(git_error)}"}

git_gateway = SafeGitGateway()
