from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(ROOT / "scripts" / "versioning"))
from bootstrap_branches import create_branch_workflow_commit


class BranchBootstrapTests(unittest.TestCase):
    def test_bootstrap_adds_beefmc_workflow_and_removes_upstream_workflows(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            repo = Path(temporary)
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
            workflow = repo / ".github" / "workflows"
            workflow.mkdir(parents=True)
            (workflow / "paper.yml").write_text("name: upstream\n", encoding="utf-8")
            (repo / "README.md").write_text("upstream source\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "upstream"], cwd=repo, check=True, capture_output=True)
            base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()

            commit = create_branch_workflow_commit(repo, "1.21.11", "version/1.21.11", base)

            self.assertIsNotNone(commit)
            self.assertEqual(base, subprocess.run(["git", "rev-parse", f"{commit}^"], cwd=repo, check=True, capture_output=True, text=True).stdout.strip())
            paths = subprocess.run(["git", "ls-tree", "-r", "--name-only", commit], cwd=repo, check=True, capture_output=True, text=True).stdout
            self.assertIn(".github/workflows/ci.yml", paths)
            self.assertNotIn(".github/workflows/paper.yml", paths)
            content = subprocess.run(["git", "show", f"{commit}:.github/workflows/ci.yml"], cwd=repo, check=True, capture_output=True, text=True).stdout
            self.assertIn("version_branch: version/1.21.11", content)
            self.assertIsNone(create_branch_workflow_commit(repo, "1.21.11", "version/1.21.11", base))


if __name__ == "__main__":
    unittest.main()
