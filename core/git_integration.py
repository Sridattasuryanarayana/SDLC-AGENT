"""
Git Integration Module - Handles all Git operations.

Features:
- Clone/pull repositories
- Create feature branches
- Stage, commit, and push changes
- Create Pull Requests via GitHub API
"""

import os
import re
import subprocess
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GitConfig:
    """Git configuration."""
    repo_url: str
    local_path: str
    main_branch: str = "main"
    github_token: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "GitConfig":
        """Load from environment variables."""
        from dotenv import load_dotenv
        load_dotenv()
        
        repo_url = os.getenv("GIT_REPO_URL", "")
        
        # Parse GitHub owner and repo from URL
        github_owner = None
        github_repo = None
        if "github.com" in repo_url:
            match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", repo_url)
            if match:
                github_owner = match.group(1)
                github_repo = match.group(2)
        
        return cls(
            repo_url=repo_url,
            local_path=os.getenv("GIT_LOCAL_PATH", "./workspace"),
            main_branch=os.getenv("GIT_MAIN_BRANCH", "main"),
            github_token=os.getenv("GITHUB_TOKEN"),
            github_owner=github_owner or os.getenv("GITHUB_OWNER"),
            github_repo=github_repo or os.getenv("GITHUB_REPO"),
        )


class GitIntegration:
    """
    Handles Git operations for the SDLC workflow.
    
    Supports:
    - Local git commands (clone, pull, branch, commit, push)
    - GitHub API for PR creation
    """
    
    def __init__(self, config: Optional[GitConfig] = None):
        """Initialize Git integration."""
        self.config = config or GitConfig.from_env()
        self.repo_path = Path(self.config.local_path)
        self._ensure_repo()
    
    def _ensure_repo(self) -> None:
        """Ensure repository is cloned and up to date."""
        if not self.repo_path.exists():
            self.repo_path.mkdir(parents=True, exist_ok=True)
        
        git_dir = self.repo_path / ".git"
        
        if not git_dir.exists():
            if self.config.repo_url:
                self.clone()
            else:
                # Initialize empty repo if no URL
                self._run_git("init")
                self._run_git("checkout", "-b", self.config.main_branch)
    
    def _run_git(self, *args, capture_output: bool = True) -> Tuple[int, str, str]:
        """Run a git command."""
        cmd = ["git"] + list(args)
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=capture_output,
            text=True
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    
    def clone(self) -> bool:
        """Clone the repository."""
        if not self.config.repo_url:
            print("No repository URL configured")
            return False
        
        print(f"Cloning {self.config.repo_url}...")
        
        # Clone to parent and move
        parent = self.repo_path.parent
        name = self.repo_path.name
        
        result = subprocess.run(
            ["git", "clone", self.config.repo_url, name],
            cwd=parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Clone failed: {result.stderr}")
            return False
        
        print("Clone successful")
        return True
    
    def pull(self, branch: Optional[str] = None) -> bool:
        """Pull latest changes from remote."""
        branch = branch or self.config.main_branch
        
        # Checkout main branch first
        self._run_git("checkout", branch)
        
        code, out, err = self._run_git("pull", "origin", branch)
        if code != 0:
            print(f"Pull failed: {err}")
            return False
        
        print(f"Pulled latest from {branch}")
        return True
    
    def create_branch(self, branch_name: str) -> bool:
        """Create and checkout a new branch."""
        # First pull latest main
        self.pull()
        
        # Create new branch from main
        code, out, err = self._run_git("checkout", "-b", branch_name)
        if code != 0:
            # Branch might exist, try checking out
            code, out, err = self._run_git("checkout", branch_name)
            if code != 0:
                print(f"Failed to create/checkout branch: {err}")
                return False
        
        print(f"Created and checked out branch: {branch_name}")
        return True
    
    def get_current_branch(self) -> str:
        """Get the current branch name."""
        code, out, err = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        return out if code == 0 else ""
    
    def stage_files(self, files: Optional[List[str]] = None) -> bool:
        """Stage files for commit."""
        if files:
            for file in files:
                self._run_git("add", file)
        else:
            self._run_git("add", "-A")
        
        return True
    
    def commit(self, message: str) -> bool:
        """Commit staged changes."""
        code, out, err = self._run_git("commit", "-m", message)
        if code != 0:
            if "nothing to commit" in err or "nothing to commit" in out:
                print("Nothing to commit")
                return True
            print(f"Commit failed: {err}")
            return False
        
        print(f"Committed: {message}")
        return True
    
    def push(self, branch: Optional[str] = None, set_upstream: bool = True) -> bool:
        """Push changes to remote."""
        branch = branch or self.get_current_branch()
        
        if set_upstream:
            code, out, err = self._run_git("push", "-u", "origin", branch)
        else:
            code, out, err = self._run_git("push", "origin", branch)
        
        if code != 0:
            print(f"Push failed: {err}")
            return False
        
        print(f"Pushed to origin/{branch}")
        return True
    
    def get_changed_files(self) -> List[str]:
        """Get list of changed files."""
        code, out, err = self._run_git("diff", "--name-only", "HEAD")
        if out:
            return out.split("\n")
        
        # Also check staged files
        code, out, err = self._run_git("diff", "--staged", "--name-only")
        if out:
            return out.split("\n")
        
        return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get repository status."""
        code, out, err = self._run_git("status", "--porcelain")
        
        modified = []
        added = []
        deleted = []
        
        for line in out.split("\n"):
            if not line:
                continue
            status = line[:2]
            filename = line[3:]
            
            if "M" in status:
                modified.append(filename)
            elif "A" in status or "?" in status:
                added.append(filename)
            elif "D" in status:
                deleted.append(filename)
        
        return {
            "branch": self.get_current_branch(),
            "modified": modified,
            "added": added,
            "deleted": deleted,
            "total_changes": len(modified) + len(added) + len(deleted)
        }
    
    def write_file(self, path: str, content: str) -> str:
        """Write content to a file in the repo."""
        full_path = self.repo_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return str(full_path)
    
    def read_file(self, path: str) -> Optional[str]:
        """Read content from a file in the repo."""
        full_path = self.repo_path / path
        if not full_path.exists():
            return None
        
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def list_files(self, pattern: str = "**/*") -> List[str]:
        """List files in the repository."""
        files = []
        for path in self.repo_path.glob(pattern):
            if path.is_file() and ".git" not in str(path):
                files.append(str(path.relative_to(self.repo_path)))
        return files
    
    def generate_branch_name(self, task_id: str, task_title: str) -> str:
        """Generate a valid branch name from task info."""
        # Clean title for branch name
        clean_title = re.sub(r"[^a-zA-Z0-9\s-]", "", task_title.lower())
        clean_title = re.sub(r"\s+", "-", clean_title)[:40]
        return f"feature/{task_id.lower()}-{clean_title}"


class GitHubPRCreator:
    """
    Creates Pull Requests using GitHub API.
    """
    
    def __init__(self, token: str, owner: str, repo: str):
        """Initialize GitHub PR creator."""
        self.token = token
        self.owner = owner
        self.repo = repo
        self.api_base = "https://api.github.com"
    
    def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None
    ) -> Tuple[int, Dict]:
        """Make GitHub API request."""
        import requests
        
        url = f"{self.api_base}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        
        response = requests.request(
            method,
            url,
            headers=headers,
            json=data,
            timeout=30
        )
        
        return response.status_code, response.json() if response.text else {}
    
    def create_pr(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        draft: bool = False
    ) -> Dict[str, Any]:
        """
        Create a pull request.
        
        Args:
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch
            draft: Create as draft PR
            
        Returns:
            PR details including number and URL
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/pulls"
        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
            "draft": draft
        }
        
        status, response = self._request("POST", endpoint, data)
        
        if status == 201:
            return {
                "success": True,
                "pr_number": response["number"],
                "pr_url": response["html_url"],
                "state": response["state"],
                "created_at": response["created_at"]
            }
        else:
            return {
                "success": False,
                "error": response.get("message", "Unknown error"),
                "errors": response.get("errors", [])
            }
    
    def get_pr(self, pr_number: int) -> Dict[str, Any]:
        """Get PR details."""
        endpoint = f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
        status, response = self._request("GET", endpoint)
        
        if status == 200:
            return {
                "success": True,
                "pr_number": response["number"],
                "state": response["state"],
                "merged": response.get("merged", False),
                "mergeable": response.get("mergeable"),
                "title": response["title"],
                "url": response["html_url"]
            }
        else:
            return {"success": False, "error": response.get("message")}
    
    def list_prs(self, state: str = "open") -> List[Dict]:
        """List pull requests."""
        endpoint = f"/repos/{self.owner}/{self.repo}/pulls?state={state}"
        status, response = self._request("GET", endpoint)
        
        if status == 200:
            return [
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "url": pr["html_url"],
                    "head_branch": pr["head"]["ref"],
                    "base_branch": pr["base"]["ref"]
                }
                for pr in response
            ]
        return []
    
    def is_pr_merged(self, pr_number: int) -> bool:
        """Check if PR is merged."""
        pr_info = self.get_pr(pr_number)
        return pr_info.get("merged", False)
    
    def add_comment(self, pr_number: int, comment: str) -> bool:
        """Add a comment to a PR."""
        endpoint = f"/repos/{self.owner}/{self.repo}/issues/{pr_number}/comments"
        status, response = self._request("POST", endpoint, {"body": comment})
        return status == 201
    
    def add_labels(self, pr_number: int, labels: List[str]) -> bool:
        """Add labels to a PR."""
        endpoint = f"/repos/{self.owner}/{self.repo}/issues/{pr_number}/labels"
        status, response = self._request("POST", endpoint, {"labels": labels})
        return status == 200
    
    def request_review(self, pr_number: int, reviewers: List[str]) -> bool:
        """Request review from specific users."""
        endpoint = f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/requested_reviewers"
        status, response = self._request("POST", endpoint, {"reviewers": reviewers})
        return status == 201


if __name__ == "__main__":
    # Test Git integration
    config = GitConfig(
        repo_url="",
        local_path="./test_workspace",
        main_branch="main"
    )
    
    git = GitIntegration(config)
    print(f"Status: {git.get_status()}")
