import subprocess
import sys
from .base_plugin import BasePlugin

class Flake8Checker(BasePlugin):
    """A plugin to run flake8 static analysis."""

    def run(self, repo_path: str) -> list[dict]:
        """
        Runs flake8 on the given repository path and returns a list of issues.
        """
        print("Running Flake8 checker...")
        try:
            result = subprocess.run(
                ["flake8", ".", "--select=E,W,F", "--ignore=E501,W503"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            print("Error: flake8 not found. Is it installed?", file=sys.stderr)
            return []
        except Exception as e:
            print(f"An error occurred while running flake8: {e}", file=sys.stderr)
            return []

        issues = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(":")
            if len(parts) >= 4:
                try:
                    issues.append({
                        "type": "flake8",
                        "file": parts[0][2:],  # remove './'
                        "line": int(parts[1]),
                        "code": parts[3].strip().split(" ")[0],
                        "message": " ".join(parts[3].strip().split(" ")[1:]),
                    })
                except (ValueError, IndexError):
                    print(f"Could not parse flake8 output line: {line}", file=sys.stderr)
        
        print(f"Flake8 checker found {len(issues)} issues.")
        return issues 