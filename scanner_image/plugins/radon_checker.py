from .base_plugin import BasePlugin
from radon.complexity import cc_visit
import os
import sys

class RadonChecker(BasePlugin):
    """A plugin to analyze code complexity using Radon."""

    def run(self, repo_path: str) -> list[dict]:
        """
        Scans Python files for cyclomatic complexity.
        """
        print("Running Radon checker...")
        issues = []

        try:
            # Walk through all Python files in the repository
            for root, _, files in os.walk(repo_path):
                if '.git' in root:
                    continue
                for file in files:
                    if file.endswith('.py'):
                        filepath = os.path.join(root, file)
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                code = f.read()
                            
                            # Use cc_visit to get complexity results
                            complexity_results = cc_visit(code)
                            
                            for result in complexity_results:
                                if result.complexity > 10:  # Only report functions with complexity > 10
                                    issues.append({
                                        "type": "radon_complexity",
                                        "file": os.path.relpath(filepath, repo_path),
                                        "line": result.lineno,
                                        "code": f"Complexity-{result.complexity}",
                                        "message": f"{result.name} has a cyclomatic complexity of {result.complexity}",
                                    })
                        except Exception as e:
                            # Ignore files that can't be read or parsed
                            print(f"Radon could not analyze file {filepath}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"An error occurred during Radon analysis: {e}", file=sys.stderr)

        print(f"Radon checker found {len(issues)} issues.")
        return issues 